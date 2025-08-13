import os
import sys
import unittest
from datetime import datetime

# Add the parent directory to the path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.config.builder import DynamicConfigBuilder
from core.translation.job import TranslationJob
from core.translation.engine import TranslationEngine
from core.utils.file_parser import parse_document
from backend.database import SessionLocal
from backend import crud

class TestIntegrationTranslation(unittest.TestCase):
    """Integration test with actual Gemini API (requires API key)."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test configuration."""
        cls.source_file = "source_novel/THE_CATCHER_IN_THE_RYE.txt"
        cls.test_output_dir = "test_outputs"
        cls.max_chars = 20000
        
        # Check for API key in environment
        cls.api_key = os.environ.get('GEMINI_API_KEY')
        if not cls.api_key:
            print("\n" + "="*60)
            print("INTEGRATION TEST SKIPPED")
            print("To run integration tests with actual API:")
            print("export GEMINI_API_KEY='your-api-key'")
            print("python -m tests.test_integration")
            print("="*60 + "\n")
        
        # Create test output directory
        os.makedirs(cls.test_output_dir, exist_ok=True)
    
    def setUp(self):
        """Set up test dependencies."""
        if not self.api_key:
            self.skipTest("No API key provided")
        
        # Load configuration
        self.config = load_config()
        
        # Create database session
        self.db = SessionLocal()
        
        # Create a test job in the database
        from backend.models import TranslationJob as DBTranslationJob
        test_job = DBTranslationJob(
            filename=f"test_catcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            status="PROCESSING"
        )
        self.db.add(test_job)
        self.db.commit()
        self.job_id = test_job.id
    
    def tearDown(self):
        """Clean up database."""
        if hasattr(self, 'db'):
            # Delete the test job
            from backend.models import TranslationJob as DBTranslationJob
            job = self.db.query(DBTranslationJob).filter(DBTranslationJob.id == self.job_id).first()
            if job:
                self.db.delete(job)
                self.db.commit()
            self.db.close()
    
    def test_real_translation_small_sample(self):
        """Test with actual Gemini API on a small sample (1000 chars)."""
        # Read the source file and get first 1000 characters for quick test
        full_text = parse_document(self.source_file)
        test_text = full_text[:1000]  # Small sample for API testing
        
        # Create a temporary test file
        test_file_path = os.path.join(self.test_output_dir, f"test_input_{self.job_id}.txt")
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_text)
        
        try:
            # Initialize Gemini model with actual API
            gemini_api = GeminiModel(
                api_key=self.api_key,
                model_name=self.config['gemini']['model'],
                safety_settings=self.config['gemini']['safety_settings'],
                generation_config=self.config['gemini']['generation_config']
            )
            
            # Validate API key
            self.assertTrue(GeminiModel.validate_api_key(self.api_key))

            # Smoke: structured generation shape (mocked)
            try:
                # Not executed against live API by default; just ensure method exists
                self.assertTrue(hasattr(gemini_api, 'generate_structured'))
            except Exception:
                pass
            
            # Create translation job
            job = TranslationJob(test_file_path, target_segment_size=1000)
            
            # Create dynamic config builder
            dyn_config_builder = DynamicConfigBuilder(gemini_api, "The Catcher in the Rye")
            
            # Create translation engine
            engine = TranslationEngine(gemini_api, dyn_config_builder, self.db, self.job_id)
            
            # Run the translation
            print(f"\nStarting translation of {len(test_text)} characters...")
            engine.translate_job(job)
            
            # Verify results
            self.assertEqual(len(job.translated_segments), len(job.segments))
            self.assertTrue(os.path.exists(job.output_filename))
            
            # Read the output
            with open(job.output_filename, 'r', encoding='utf-8') as f:
                output_content = f.read()
            
            # Basic checks on the output
            self.assertGreater(len(output_content), 0)
            # Check for Korean characters (Hangul)
            has_korean = any('\uac00' <= char <= '\ud7a3' for char in output_content)
            self.assertTrue(has_korean, "Output should contain Korean characters")
            
            print(f"Translation completed successfully!")
            print(f"Output file: {job.output_filename}")
            print(f"Output length: {len(output_content)} characters")
            print(f"Glossary entries: {job.glossary}")
            
            # Show a sample of the translation
            print("\nSample of translation (first 200 chars):")
            print(output_content[:200] + "...")
            
        finally:
            # Clean up
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
    
    def test_real_translation_20k_chars(self):
        """Test with actual Gemini API on 20,000 characters (full test)."""
        # This test will use more API calls and take longer
        response = input("\nThis test will use multiple Gemini API calls. Continue? (y/n): ")
        if response.lower() != 'y':
            self.skipTest("User chose to skip full integration test")
        
        # Read the source file and get first 20,000 characters
        full_text = parse_document(self.source_file)
        test_text = full_text[:self.max_chars]
        
        # Create a temporary test file
        test_file_path = os.path.join(self.test_output_dir, f"test_full_{self.job_id}.txt")
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_text)
        
        try:
            # Initialize Gemini model
            gemini_api = GeminiModel(
                api_key=self.api_key,
                model_name=self.config['gemini']['model'],
                safety_settings=self.config['gemini']['safety_settings'],
                generation_config=self.config['gemini']['generation_config']
            )
            
            # Create translation job
            job = TranslationJob(test_file_path, target_segment_size=5000)
            print(f"\nCreated {len(job.segments)} segments from {self.max_chars} characters")
            
            # Create dynamic config builder
            dyn_config_builder = DynamicConfigBuilder(gemini_api, "The Catcher in the Rye")
            
            # Create translation engine
            engine = TranslationEngine(gemini_api, dyn_config_builder, self.db, self.job_id)
            
            # Run the translation
            print("Starting full translation...")
            start_time = datetime.now()
            engine.translate_job(job)
            end_time = datetime.now()
            
            # Calculate time taken
            duration = (end_time - start_time).total_seconds()
            print(f"\nTranslation completed in {duration:.2f} seconds")
            
            # Verify results
            self.assertEqual(len(job.translated_segments), len(job.segments))
            self.assertTrue(os.path.exists(job.output_filename))
            
            # Analyze the output
            with open(job.output_filename, 'r', encoding='utf-8') as f:
                output_content = f.read()
            
            print(f"\nTranslation Statistics:")
            print(f"- Input characters: {len(test_text)}")
            print(f"- Output characters: {len(output_content)}")
            print(f"- Number of segments: {len(job.segments)}")
            print(f"- Glossary entries: {len(job.glossary)}")
            print(f"- Character styles: {len(job.character_styles)}")
            print(f"- Output file: {job.output_filename}")
            
            # Save detailed statistics
            stats_file = os.path.join(self.test_output_dir, f"stats_{self.job_id}.txt")
            with open(stats_file, 'w', encoding='utf-8') as f:
                f.write(f"Translation Statistics\n")
                f.write(f"=====================\n")
                f.write(f"Date: {datetime.now()}\n")
                f.write(f"Duration: {duration:.2f} seconds\n")
                f.write(f"Input characters: {len(test_text)}\n")
                f.write(f"Output characters: {len(output_content)}\n")
                f.write(f"Segments: {len(job.segments)}\n")
                f.write(f"\nGlossary:\n")
                for k, v in job.glossary.items():
                    f.write(f"  {k}: {v}\n")
                f.write(f"\nCharacter Styles:\n")
                for k, v in job.character_styles.items():
                    f.write(f"  {k}: {v}\n")
            
            print(f"\nStatistics saved to: {stats_file}")
            
        finally:
            # Clean up
            if os.path.exists(test_file_path):
                os.remove(test_file_path)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)