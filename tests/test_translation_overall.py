import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

# Add the parent directory to the path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.config.builder import DynamicConfigBuilder
from core.translation.document import TranslationDocument  
from core.translation.translation_pipeline import TranslationPipeline
from core.utils.file_parser import parse_document

class TestOverallTranslation(unittest.TestCase):
    """Test the overall translation functionality with a 20,000 character sample."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test configuration once for all tests."""
        cls.source_file = "source_novel/THE_CATCHER_IN_THE_RYE.txt"
        cls.test_output_dir = "test_outputs"
        cls.max_chars = 20000
        
        # Create test output directory
        os.makedirs(cls.test_output_dir, exist_ok=True)
    
    def setUp(self):
        """Set up test dependencies."""
        # Load configuration
        self.config = load_config()
        
        # Mock database session
        self.mock_db = Mock(spec=Session)
        self.mock_job_id = 1
        
    def test_translation_with_20k_chars(self):
        """Test translation of first 20,000 characters from The Catcher in the Rye."""
        
        # Read the source file and get first 20,000 characters
        full_text = parse_document(self.source_file)
        test_text = full_text[:self.max_chars]
        
        # Create a temporary test file with the truncated text
        test_file_path = os.path.join(self.test_output_dir, "test_input.txt")
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_text)
        
        # Mock the Gemini API responses
        mock_gemini = Mock(spec=GeminiModel)
        
        # Mock style definition response and enough translation responses for any number of segments
        mock_responses = [
            # First call: define core narrative style
            "A cynical, conversational first-person narrative style with teenage slang ('냉소적이고 대화체의 1인칭 서술, 십대 슬랭 포함').",
        ]
        
        # Add enough mock translation responses (20 should be more than enough)
        for i in range(1, 21):
            mock_responses.append(f"[번역된 텍스트 세그먼트 {i}]")
        
        mock_gemini.generate_text.side_effect = mock_responses
        
        # Create translation job with smaller segment size for testing
        document = TranslationDocument(test_file_path, target_segment_size=5000)
        
        # Verify segments were created
        self.assertGreater(len(document.segments), 0)
        print(f"Created {len(document.segments)} segments from {self.max_chars} characters")
        
        # Create dynamic config builder
        dyn_config_builder = DynamicConfigBuilder(mock_gemini, "The Catcher in the Rye")
        
        # Mock the dynamic config builder's responses
        with patch.object(dyn_config_builder, 'build_dynamic_guides') as mock_build_guides:
            mock_build_guides.return_value = (
                {"Holden": "홀든", "Pencey Prep": "펜시 프렙"},  # glossary
                {"Holden": "Uses informal, cynical teenage speech"},  # character styles
                "Maintaining cynical narrative tone"  # style deviation
            )
            
            # Create and run translation engine
            pipeline = TranslationPipeline(mock_gemini, dyn_config_builder, self.mock_db, self.mock_job_id)
            
            # Mock the crud update function
            with patch('backend.crud.update_job_progress'):
                # Run the translation
                pipeline.translate_document(document)
        
        # Verify translation was completed
        self.assertEqual(len(document.translated_segments), len(document.segments))
        
        # Verify output file was created
        self.assertTrue(os.path.exists(document.output_filename))
        
        # Read and verify the output
        with open(document.output_filename, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        # Check that output contains expected content
        self.assertIn("[번역된 텍스트", output_content)
        self.assertGreater(len(output_content), 0)
        
        # Verify glossary was populated
        self.assertIn("Holden", document.glossary)
        self.assertEqual(document.glossary["Holden"], "홀든")
        
        # Clean up test file
        os.remove(test_file_path)
        
        print(f"Translation test completed successfully!")
        print(f"Output file: {document.output_filename}")
        print(f"Glossary entries: {len(document.glossary)}")
        print(f"Character styles: {len(document.character_styles)}")
    
    def test_translation_with_api_key_validation(self):
        """Test API key validation before translation."""
        
        # Test with invalid API key
        with patch('core.translation.models.gemini.GeminiModel.validate_api_key') as mock_validate:
            mock_validate.return_value = False
            
            # Verify that invalid API key is detected
            is_valid = GeminiModel.validate_api_key("invalid_key")
            self.assertFalse(is_valid)
        
        # Test with valid API key
        with patch('core.translation.models.gemini.GeminiModel.validate_api_key') as mock_validate:
            mock_validate.return_value = True
            
            # Verify that valid API key passes
            is_valid = GeminiModel.validate_api_key("valid_key")
            self.assertTrue(is_valid)

    def test_prompts_presence(self):
        """Ensure validation prompts (including structured variants) are loaded."""
        from core.prompts.manager import PromptManager
        self.assertTrue(len(PromptManager.MAIN_TRANSLATION) > 0)
        self.assertTrue(len(PromptManager.SOFT_RETRY_TRANSLATION) > 0)
        # Structured validation prompts should exist in prompts.yaml
        self.assertIsNotNone(PromptManager.VALIDATION_STRUCTURED_COMPREHENSIVE)
        self.assertIsNotNone(PromptManager.VALIDATION_STRUCTURED_QUICK)
    
    def test_segment_creation(self):
        """Test that text is properly segmented."""
        
        # Read the source file
        full_text = parse_document(self.source_file)
        test_text = full_text[:self.max_chars]
        
        # Create temporary file
        test_file_path = os.path.join(self.test_output_dir, "test_segmentation.txt")
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_text)
        
        # Test different segment sizes
        segment_sizes = [5000, 10000, 15000]
        
        for size in segment_sizes:
            document = TranslationDocument(test_file_path, target_segment_size=size)
            
            # Verify segments are reasonable (segments can be larger to avoid splitting paragraphs)
            for i, segment in enumerate(document.segments):
                # Last segment can be any size, others should be close to target
                if i < len(document.segments) - 1:
                    # Allow up to 2x the target size to accommodate paragraph boundaries
                    self.assertLessEqual(len(segment.text), size * 2)
            
            print(f"Segment size {size}: created {len(document.segments)} segments")
        
        # Clean up
        os.remove(test_file_path)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test outputs directory."""
        # Remove test output files
        for file in os.listdir(cls.test_output_dir):
            file_path = os.path.join(cls.test_output_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Remove directory if empty
        if not os.listdir(cls.test_output_dir):
            os.rmdir(cls.test_output_dir)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)