"""
Retry decorator for handling ProhibitedException with progressively softer prompts.
"""

import functools
import time
from typing import Callable, Any, Optional
from ..errors import ProhibitedException
from ..prompts.sanitizer import PromptSanitizer


def retry_with_softer_prompt(max_retries: int = 3, delay: float = 2.0):
    """
    Decorator that retries a function with progressively softer prompts when ProhibitedException occurs.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay in seconds between retries
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            original_prompt = None
            
            # Extract the prompt from arguments
            if 'prompt' in kwargs:
                original_prompt = kwargs['prompt']
            elif len(args) > 0 and isinstance(args[0], str):
                original_prompt = args[0]
            elif len(args) > 1 and isinstance(args[1], str):
                # For methods where self is first argument
                original_prompt = args[1]
            
            if not original_prompt:
                # If we can't find the prompt, just call the function normally
                return func(*args, **kwargs)
            
            # Try with original prompt first
            for attempt in range(max_retries + 1):
                try:
                    if attempt == 0:
                        # First attempt with original prompt
                        return func(*args, **kwargs)
                    else:
                        # Retry with softer prompt
                        print(f"\nRetrying with softer prompt (attempt {attempt}/{max_retries})...")
                        
                        # Create softer prompt
                        softer_prompt = PromptSanitizer.create_softer_prompt(original_prompt, attempt)
                        
                        # Update the prompt in arguments
                        if 'prompt' in kwargs:
                            kwargs['prompt'] = softer_prompt
                        elif len(args) > 0 and isinstance(args[0], str):
                            args = (softer_prompt,) + args[1:]
                        elif len(args) > 1 and isinstance(args[1], str):
                            # For methods where self is first argument
                            args = (args[0], softer_prompt) + args[2:]
                        
                        time.sleep(delay)
                        return func(*args, **kwargs)
                        
                except ProhibitedException as e:
                    last_exception = e
                    if attempt < max_retries:
                        print(f"\nProhibitedException caught: {e}")
                        print("Will retry with a softer prompt...")
                    else:
                        print(f"\nAll {max_retries} retry attempts with softer prompts failed.")
                        # Update exception with retry information
                        e.context = e.context or {}
                        e.context['retry_attempts'] = max_retries
                        e.context['final_prompt'] = kwargs.get('prompt', args[1] if len(args) > 1 else None)
                        raise
                    
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_on_prohibited_segment(translation_func: Callable) -> Callable:
    """
    Specialized decorator for translation segments that handles ProhibitedException
    by trying different approaches.
    """
    @functools.wraps(translation_func)
    def wrapper(self, *args, **kwargs):
        try:
            return translation_func(self, *args, **kwargs)
        except ProhibitedException as e:
            # Extract segment information
            segment_text = e.source_text or kwargs.get('segment_text', '')
            target_language = kwargs.get('target_language', 'Korean')
            
            print(f"\nSegment translation blocked. Trying minimal prompt approach...")
            
            # Try with a minimal prompt
            minimal_prompt = PromptSanitizer.create_minimal_prompt(
                segment_text, 
                target_language
            )
            
            # Get the gemini_api from self
            if hasattr(self, 'gemini_api'):
                try:
                    response = self.gemini_api.generate_text(minimal_prompt)
                    print("Successfully translated with minimal prompt.")
                    return response
                except ProhibitedException:
                    # If even minimal prompt fails, return a placeholder
                    print("Even minimal prompt failed. Returning placeholder.")
                    return f"[Content could not be translated due to safety filters]"
            else:
                raise
                
    return wrapper