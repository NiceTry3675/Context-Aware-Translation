"""
Visual Element Extractor for Illustration Generation

Extracts visual elements, cinematic details, and character descriptions from text.
"""
from typing import Dict, Any, List, Optional
import logging


class VisualElementExtractor:
    """Extracts visual elements from text for illustration generation."""

    def extract_visual_elements(self,
                               text: str,
                               glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Extract visual elements from text for illustration generation.

        Args:
            text: The text to analyze
            glossary: Optional glossary for names

        Returns:
            Dictionary of visual elements
        """
        elements = {
            'setting': None,
            'characters': [],
            'mood': None,
            'action': None
        }

        # Simple keyword-based extraction (can be enhanced with AI)
        text_lower = text.lower()

        # Extract setting
        setting_keywords = {
            'room': 'indoor room',
            'house': 'residential house',
            'street': 'urban street',
            'forest': 'forest landscape',
            'office': 'office space',
            'restaurant': 'restaurant interior',
            'park': 'public park',
            'beach': 'beach scenery',
            'mountain': 'mountain landscape',
            'castle': 'medieval castle',
            'village': 'small village',
            'city': 'modern city',
            'school': 'school building',
            'library': 'library interior',
            'garden': 'beautiful garden',
            'desert': 'desert landscape',
            'spaceship': 'spaceship interior',
            'battlefield': 'war-torn battlefield'
        }

        for keyword, setting in setting_keywords.items():
            if keyword in text_lower:
                elements['setting'] = setting
                break

        # Track which characters are present (but store names for reference)
        if glossary:
            for name in glossary.keys():
                if name in text:
                    elements['characters'].append(name)

        # Extract mood
        mood_keywords = {
            'happy': 'joyful',
            'sad': 'melancholic',
            'angry': 'tense',
            'peaceful': 'serene',
            'mysterious': 'mysterious',
            'romantic': 'romantic',
            'dark': 'dark and moody',
            'bright': 'bright and cheerful',
            'tense': 'suspenseful',
            'dramatic': 'dramatic'
        }

        for keyword, mood in mood_keywords.items():
            if keyword in text_lower:
                elements['mood'] = mood
                break

        # Extract action (simplified)
        action_keywords = {
            'running': 'person running',
            'talking': 'people in conversation',
            'walking': 'person walking',
            'sitting': 'person sitting',
            'eating': 'people dining',
            'working': 'person working',
            'reading': 'person reading',
            'fighting': 'intense combat',
            'dancing': 'people dancing',
            'sleeping': 'person sleeping',
            'studying': 'person studying',
            'cooking': 'person cooking'
        }

        for keyword, action in action_keywords.items():
            if keyword in text_lower:
                elements['action'] = action
                break

        return elements

    def extract_cinematic_details(self, text: str) -> Dict[str, Any]:
        """
        Lightweight heuristics to enrich prompts with cinematic details.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with keys: time_of_day, weather, lighting, camera_distance, camera_angle, key_objects
        """
        t = (text or "").lower()
        out: Dict[str, Any] = {}

        # Time of day
        if any(k in t for k in ["dawn", "sunrise", "first light"]):
            out['time_of_day'] = 'dawn'
        elif any(k in t for k in ["morning", "forenoon"]):
            out['time_of_day'] = 'morning'
        elif any(k in t for k in ["noon", "midday"]):
            out['time_of_day'] = 'noon'
        elif any(k in t for k in ["afternoon", "sunset", "twilight", "dusk"]):
            out['time_of_day'] = 'late afternoon / dusk'
        elif any(k in t for k in ["night", "midnight", "moon", "stars", "lamplight", "candlelight"]):
            out['time_of_day'] = 'night'

        # Weather
        if any(k in t for k in ["rain", "drizzle", "shower"]):
            out['weather'] = 'rainy'
        elif any(k in t for k in ["storm", "thunder", "lightning"]):
            out['weather'] = 'stormy'
        elif any(k in t for k in ["fog", "mist", "haze"]):
            out['weather'] = 'foggy'
        elif any(k in t for k in ["snow", "blizzard"]):
            out['weather'] = 'snowy'
        elif 'wind' in t:
            out['weather'] = 'windy'
        elif 'sunny' in t or 'clear' in t:
            out['weather'] = 'clear'

        # Lighting (prioritized from explicit cues and consistent with time of day)
        time_of_day = out.get('time_of_day', '')

        # Explicit light sources take precedence
        if 'candle' in t or 'candlelight' in t or 'lantern' in t or 'lamplight' in t:
            out['lighting'] = 'warm candle/lamplight with soft falloff'
        # For night scenes, use appropriate night lighting
        elif time_of_day == 'night' or ('moon' in t or 'moonlight' in t):
            out['lighting'] = 'cool moonlight with gentle shadows' if 'moon' in t else 'dim nighttime ambient light'
        # For morning/day scenes, use daylight
        elif time_of_day in ['morning', 'noon', 'dawn'] or any(k in t for k in ['window', 'sun', 'daylight', 'sunlight']):
            out['lighting'] = 'soft morning light' if time_of_day == 'morning' else 'natural daylight'
        elif time_of_day == 'late afternoon / dusk':
            out['lighting'] = 'warm golden-hour light'
        elif out.get('weather') == 'rainy' or 'overcast' in t:
            out['lighting'] = 'overcast diffuse lighting'
        # Default based on time
        elif time_of_day:
            out['lighting'] = 'appropriate ambient light for ' + time_of_day

        # Camera cues
        out.setdefault('camera_distance', 'medium or wide')
        out.setdefault('camera_angle', 'eye-level')
        if any(k in t for k in ["tower", "castle gate", "statue towering", "cathedral"]):
            out['camera_angle'] = 'low-angle'
        if any(k in t for k in ["balcony", "cliff", "overlook", "overhead", "mezzanine"]):
            out['camera_angle'] = 'high-angle'

        # Key objects (very small curated list)
        objects_map = [
            ("sword", "sword"), ("blade", "blade"), ("shield", "shield"), ("book", "book"),
            ("letter", "letter"), ("window", "window"), ("desk", "desk"), ("table", "table"),
            ("candle", "candle"), ("lantern", "lantern"), ("armor", "armor"), ("cup", "cup"),
            ("bottle", "bottle"), ("painting", "painting"), ("fireplace", "fireplace"),
            ("crown", "crown"), ("throne", "throne"), ("map", "map"), ("scroll", "scroll")
        ]
        found = []
        for kw, label in objects_map:
            if kw in t:
                found.append(label)
        # Keep it short to avoid over-specification
        out['key_objects'] = found[:4]

        return out

    def get_character_descriptions(self, character_names: List[str], segment_text: str) -> List[str]:
        """
        Convert character names to generic visual descriptions for illustration.
        Avoids using actual names to prevent them from appearing as text in images.

        Args:
            character_names: List of character names found in the segment
            segment_text: The text segment for context

        Returns:
            List of generic character descriptions
        """
        descriptions = []

        # Map common character archetypes based on context clues
        text_lower = segment_text.lower()

        # Create more varied descriptions based on the number of characters
        num_characters = len(character_names)

        if num_characters == 1:
            # Single character - try to be more descriptive
            if any(word in text_lower for word in ['child', 'boy', 'kid', 'young']):
                descriptions.append("a young boy")
            elif any(word in text_lower for word in ['girl', 'young woman']):
                descriptions.append("a young woman")
            elif any(word in text_lower for word in ['woman', 'lady', 'female']):
                descriptions.append("a woman")
            elif any(word in text_lower for word in ['man', 'gentleman', 'male']):
                descriptions.append("a man")
            elif any(word in text_lower for word in ['old', 'elderly', 'aged', 'senior']):
                descriptions.append("an elderly person")
            else:
                descriptions.append("a person")

        elif num_characters == 2:
            # Two characters - show them in conversation or interaction
            if any(word in text_lower for word in ['talking', 'conversation', 'discussing', 'arguing']):
                descriptions.append("two people in conversation")
            elif any(word in text_lower for word in ['fighting', 'combat', 'battle']):
                descriptions.append("two people in confrontation")
            elif any(word in text_lower for word in ['embracing', 'hugging', 'holding']):
                descriptions.append("two people embracing")
            else:
                descriptions.append("two people together")

        elif num_characters >= 3:
            # Multiple characters - describe as a group
            if any(word in text_lower for word in ['meeting', 'gathering', 'assembled']):
                descriptions.append("a group of people gathered")
            elif any(word in text_lower for word in ['crowd', 'audience']):
                descriptions.append("a crowd of people")
            elif any(word in text_lower for word in ['team', 'squad', 'group']):
                descriptions.append("a team of people")
            else:
                descriptions.append(f"a group of {num_characters} people")

        # If we still have no descriptions, use generic fallback
        if not descriptions:
            if num_characters == 1:
                descriptions.append("a person")
            elif num_characters == 2:
                descriptions.append("two people")
            else:
                descriptions.append("several people")

        return descriptions

    def infer_world_hints(self, text: Optional[str]) -> Dict[str, str]:
        """
        Infer high-level world/genre hints from text without over-specifying details.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with genre and period hints
        """
        if not text:
            return {}

        t = text.lower()
        hints: Dict[str, str] = {}

        # Very lightweight heuristics
        fantasy_kw = ["castle", "kingdom", "sword", "knight", "mage", "dungeon", "dragon", "guild", "magic", "wizard", "sorcerer"]
        scifi_kw = ["starship", "spaceship", "planet", "galaxy", "alien", "android", "cyber", "neon", "hacking", "quantum", "laser", "robot"]
        historical_kw = ["emperor", "dynasty", "samurai", "shogun", "roman", "medieval", "victorian", "monarchy", "feudal"]
        contemporary_kw = ["school", "classroom", "university", "subway", "smartphone", "apartment", "office", "cafe", "city", "computer", "internet"]

        def contains_any(words):
            return any(w in t for w in words)

        if contains_any(fantasy_kw):
            hints["genre"] = "fantasy"
        elif contains_any(scifi_kw):
            hints["genre"] = "sci-fi"
        elif contains_any(historical_kw):
            hints["genre"] = "historical"
        elif contains_any(contemporary_kw):
            hints["genre"] = "contemporary"

        # Very light period cue
        if "medieval" in t or "castle" in t or "knight" in t:
            hints["period"] = "medieval"
        elif "victorian" in t:
            hints["period"] = "victorian"
        elif any(k in t for k in ["neon", "cyber", "android", "ai overload"]):
            hints["period"] = "near-future"
        else:
            hints.setdefault("period", "unspecified")

        return hints

    def create_prompt_from_atmosphere(self, world_atmosphere, segment_text: str,
                                     glossary: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Create visual elements from AI-analyzed world atmosphere data.

        Args:
            world_atmosphere: WorldAtmosphereAnalysis object with rich context
            segment_text: The text segment
            glossary: Optional glossary for names

        Returns:
            Dictionary of visual elements optimized for illustration
        """
        illustration_context = world_atmosphere.to_illustration_context()

        elements = {
            'setting': illustration_context.get('setting', ''),
            'characters': [],
            'mood': illustration_context.get('mood', ''),
            'action': None,
            'lighting': illustration_context.get('lighting', ''),
            'colors': illustration_context.get('colors', []),
            'weather': illustration_context.get('weather', ''),
            'time': illustration_context.get('time', ''),
            'tension': illustration_context.get('tension', ''),
            'dramatic_weight': illustration_context.get('dramatic_weight', 'medium'),
            'summary': illustration_context.get('summary', '')
        }

        # Extract characters from glossary if they appear in the summary (if available) or text
        if glossary:
            # Use summary if available for more accurate character identification
            search_text = elements.get('summary', segment_text) or segment_text
            for name in glossary.keys():
                if name in search_text:
                    elements['characters'].append(name)

        # Determine action based on narrative focus
        focus = illustration_context.get('focus', '')
        if 'conversation' in focus.lower() or 'dialogue' in focus.lower():
            elements['action'] = 'people in conversation'
        elif 'action' in focus.lower() or 'movement' in focus.lower():
            elements['action'] = 'dynamic movement'
        elif 'contemplation' in focus.lower() or 'thinking' in focus.lower():
            elements['action'] = 'quiet contemplation'

        # Enhance mood with tension and dramatic weight
        if elements['tension'] == 'climactic' or elements['dramatic_weight'] == 'high':
            elements['mood'] = f"intense and {elements['mood']}"
        elif elements['tension'] == 'calm':
            elements['mood'] = f"peaceful and {elements['mood']}"

        return elements