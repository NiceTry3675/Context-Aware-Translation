"""
Prompt Builder for Illustration Generation

Builds various prompts for illustration generation including scene prompts,
character base prompts, and prompts with character profiles.
"""
from typing import Dict, Any, Optional, List
import logging


class IllustrationPromptBuilder:
    """Builds prompts for illustration generation."""

    def __init__(self, visual_extractor):
        """
        Initialize the prompt builder.

        Args:
            visual_extractor: VisualElementExtractor instance
        """
        self.visual_extractor = visual_extractor

    def _get_style_description(self, style: Optional[str]) -> str:
        """
        Convert style enum value to descriptive prompt text.

        Args:
            style: IllustrationStyle value (e.g., 'realistic', 'watercolor', 'anime')

        Returns:
            Style description for prompt
        """
        if not style or style == 'default':
            return "High quality, detailed"

        style_lower = str(style).lower()
        style_map = {
            'realistic': "Photorealistic render, highly detailed textures, natural lighting, lifelike, professional photography quality",
            'artistic': "Artistic illustration with painterly style, expressive brushwork, high quality, detailed background",
            'watercolor': "Watercolor painting style with soft blending, translucent colors, high quality, detailed background",
            'digital_art': "Digital art illustration with clean lines, vibrant colors, high quality, detailed background",
            'sketch': "Sketch art style with pencil or ink lines, loose artistic rendering, high quality",
            'anime': "Anime/manga illustration style with clean linework, vibrant colors, high quality, detailed background",
            'vintage': "Vintage art style with retro aesthetics, muted tones, high quality, detailed background",
            'minimalist': "Minimalist illustration with simple shapes, limited color palette, clean composition, high quality"
        }

        return style_map.get(style_lower, "High quality, detailed")

    def create_illustration_prompt(self,
                                 segment_text: str,
                                 context: Optional[str] = None,
                                 style_hints: str = "",
                                 glossary: Optional[Dict[str, str]] = None,
                                 world_atmosphere=None,
                                 style: Optional[str] = None) -> str:
        """
        Create an illustration prompt from segment text.

        Args:
            segment_text: The text segment to illustrate
            context: Optional context from previous segments
            style_hints: Style preferences for the illustration
            glossary: Optional glossary for character/place names
            world_atmosphere: World and atmosphere analysis data
            style: Illustration style (realistic, watercolor, anime, etc.)

        Returns:
            Generated prompt for image generation
        """
        # Use AI-analyzed world atmosphere if available, otherwise fall back to keyword extraction
        if world_atmosphere:
            visual_elements = self.visual_extractor.create_prompt_from_atmosphere(
                world_atmosphere, segment_text, glossary
            )
            extraction_method = 'world_atmosphere'
            # Use summary from world atmosphere for better context
            effective_text = segment_text
            if hasattr(world_atmosphere, 'segment_summary'):
                if world_atmosphere.segment_summary:
                    effective_text = world_atmosphere.segment_summary
            elif isinstance(world_atmosphere, dict) and 'segment_summary' in world_atmosphere:
                if world_atmosphere['segment_summary']:
                    effective_text = world_atmosphere['segment_summary']
        else:
            # Fallback to simple keyword extraction
            visual_elements = self.visual_extractor.extract_visual_elements(segment_text, glossary)
            extraction_method = 'keyword_extraction'
            effective_text = segment_text

        # Build a more descriptive, image-friendly prompt
        base_description = []

        # If we have a summary from world atmosphere, incorporate it into the prompt
        if visual_elements.get('summary'):
            # Start with a more narrative-driven description based on the summary
            base_description.append(f"A scene depicting: {visual_elements['summary'][:100]}")
            if visual_elements.get('setting'):
                base_description.append(f"Taking place in {visual_elements['setting']}")
        else:
            # Fallback to the old method
            if visual_elements.get('setting'):
                base_description.append(f"A scene in {visual_elements['setting']}")
            else:
                base_description.append("A scene")

        # Add characters with visual descriptions (without names)
        if visual_elements.get('characters'):
            character_descriptions = self.visual_extractor.get_character_descriptions(
                visual_elements['characters'], effective_text
            )
            if character_descriptions:
                if len(character_descriptions) == 1:
                    base_description.append(f"featuring {character_descriptions[0]}")
                else:
                    base_description.append(f"featuring {', '.join(character_descriptions)}")

        # Add action
        if visual_elements.get('action'):
            base_description.append(f"with {visual_elements['action']}")

        # Add mood/atmosphere
        if visual_elements.get('mood'):
            base_description.append(f"in a {visual_elements['mood']} atmosphere")

        # Combine the base description
        prompt = " ".join(base_description)

        # Add lightweight cinematic details (time, weather, lighting, camera, key objects)
        # Use the summary from world_atmosphere if available for more focused details
        merged_text = (context + "\n" + effective_text) if context else effective_text
        cine = self.visual_extractor.extract_cinematic_details(merged_text)

        details = []
        if cine.get('time_of_day'):
            details.append(f"time of day: {cine['time_of_day']}")
        if cine.get('weather'):
            details.append(f"weather: {cine['weather']}")
        if cine.get('lighting'):
            details.append(f"lighting: {cine['lighting']}")

        # Camera composition
        if cine.get('camera_distance') or cine.get('camera_angle'):
            cd = cine.get('camera_distance') or 'medium or wide'
            ca = cine.get('camera_angle') or 'eye-level'
            details.append(f"compose as a {cd} shot at {ca} angle; include foreground, midground, and background for depth")

        # Key objects (limited)
        if cine.get('key_objects'):
            details.append(f"include key objects: {', '.join(cine['key_objects'])}")

        if details:
            prompt = f"{prompt}. " + ". ".join(details)

        # Add style hints at the beginning if provided
        if style_hints:
            prompt = f"{style_hints}. {prompt}"

        # Add artistic style at the end (using style parameter)
        style_description = self._get_style_description(style)
        prompt += f". {style_description}"

        # Make sure prompt is safe and appropriate
        original_prompt = prompt
        prompt = prompt.replace("violent", "dramatic")
        prompt = prompt.replace("blood", "intense")
        prompt = prompt.replace("death", "dramatic moment")

        logging.info(f"Generated prompt for image: {prompt[:150]}...")

        return prompt

    def create_character_base_prompt(self,
                                    profile: Dict[str, Any],
                                    style_hints: str = "",
                                    context_text: Optional[str] = None,
                                    style: Optional[str] = None) -> str:
        """
        Build a minimal prompt anchored on the protagonist's name only.

        Keeps details sparse to avoid over-specification and downstream lock-in.

        Args:
            profile: Character profile dictionary
            style_hints: Optional style hints
            context_text: Optional context text for world inference
            style: Illustration style (realistic, watercolor, anime, etc.)

        Returns:
            Character base prompt
        """
        name = str(profile.get('name') or 'Protagonist')

        parts: List[str] = []
        # Optional global style hints (kept generic if present)
        if style_hints:
            parts.append(style_hints)
        if profile.get('extra_style_hints'):
            parts.append(str(profile['extra_style_hints']))

        # High-level world hints inferred from text
        world = self.visual_extractor.infer_world_hints(context_text)
        if world.get("genre"):
            parts.append(f"genre: {world['genre']}")
        if world.get("period") and world['period'] != 'unspecified':
            parts.append(f"period vibe: {world['period']}")

        # Minimal identity; instruct NOT to render text or name
        parts.append(
            f"Character design portrait of {name}. Do not include any background."
        )

        # Use style parameter if provided, otherwise fall back to profile style
        effective_style = style or profile.get('style')
        style_pref = str(effective_style or '').lower()

        # Apply style-specific description for character design
        if style_pref == 'default' or not style_pref:
            parts.append("Character design, high quality")
        elif style_pref == 'anime':
            parts.append("Anime character design, clean linework, high quality")
        elif style_pref == 'realistic':
            parts.append("Photorealistic character portrait, lifelike details, professional photography, studio lighting")
        elif style_pref == 'watercolor':
            parts.append("Watercolor character portrait, soft colors, high quality")
        elif style_pref == 'sketch':
            parts.append("Sketch character design, pencil or ink lines, high quality")
        elif style_pref == 'artistic':
            parts.append("Artistic character portrait, painterly style, high quality")
        elif style_pref in ['digital_art', 'vintage', 'minimalist']:
            parts.append("Digital illustration character design, high quality, consistent lighting")
        else:
            parts.append("Character design, high quality")

        return ". ".join(parts)

    def create_scene_prompt_with_profile(self,
                                        segment_text: str,
                                        context: Optional[str],
                                        profile: Dict[str, Any],
                                        style_hints: str = "",
                                        style: Optional[str] = None) -> str:
        """
        Compose a richer scene prompt with profile lock and cinematic details.

        - Locks visual identity from `profile`.
        - Extracts setting/action/mood plus cinematic cues (time, weather, lighting, camera).
        - Uses optional previous context to improve extraction.

        Args:
            segment_text: Current segment text
            context: Previous context
            profile: Character profile for consistency
            style_hints: Optional style hints
            style: Illustration style (realistic, watercolor, anime, etc.)

        Returns:
            Scene prompt with character consistency
        """
        # Consistency lock
        lock_items = []
        for key in ['hair_color', 'hair_style', 'eye_color', 'eye_shape', 'skin_tone',
                   'body_type', 'clothing', 'accessories']:
            val = profile.get(key)
            if val:
                lock_items.append(f"{key.replace('_', ' ')}: {val}")
        lock_text = "; ".join(lock_items)
        lock_clause = (
            f"Maintain the exact same character appearance ({lock_text}). Do not change these traits"
            if lock_text else
            "Maintain the same character appearance as previously defined"
        )

        # Merge current segment with brief previous context for better signal
        merged_text = segment_text
        if context:
            merged_text = (context + "\n" + segment_text)

        # Extract visual elements to emphasize scene context
        elements = self.visual_extractor.extract_visual_elements(merged_text, glossary=None)
        setting_txt = elements.get('setting') or 'an appropriate environment'
        action_txt = elements.get('action') or 'a context-appropriate action'
        mood_txt = elements.get('mood') or None

        # Add cinematic details
        cine = self.visual_extractor.extract_cinematic_details(merged_text)

        # Strong scene directive (avoid portraits when scene demanded)
        scene_directives = [
            f"Place the character in {setting_txt}",
            f"showing {action_txt}",
            # Camera details
            (
                f"compose as a {cine['camera_distance']} shot at {cine['camera_angle']} angle"
                if cine.get('camera_distance') and cine.get('camera_angle')
                else "compose as a medium or wide shot (not a simple portrait)"
            ),
            "include foreground, midground, and background for depth",
            "include background elements matching the environment, with depth and lighting",
        ]
        if mood_txt:
            scene_directives.append(f"overall atmosphere: {mood_txt}")

        # Time/weather/lighting and key objects
        if cine.get('time_of_day'):
            scene_directives.append(f"time of day: {cine['time_of_day']}")
        if cine.get('weather'):
            scene_directives.append(f"weather: {cine['weather']}")
        if cine.get('lighting'):
            scene_directives.append(f"lighting: {cine['lighting']}")
        if cine.get('key_objects'):
            scene_directives.append(f"include key objects: {', '.join(cine['key_objects'])}")

        base_scene = ". ".join(scene_directives)

        # Strengthen constraints
        # Style hints come first to bias rendering
        prefix = (style_hints + ". ") if style_hints else ""
        scene_prompt = f"{prefix}{lock_clause}. {base_scene}. No text or watermark in the image. Cinematic composition, high quality."
        # Apply style description based on config
        style_description = self._get_style_description(style)
        scene_prompt += f". {style_description}"

        return scene_prompt