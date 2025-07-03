class PromptBuilder:
    """
    A simple template engine to build the final prompt.
    """
    def __init__(self, template_path="prompt_template.md"):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                self.template = f.read()
            print("Prompt template loaded successfully.")
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template file not found at: {template_path}")

    def create_prompt(self, context_data: dict) -> str:
        """
        Builds the final prompt by filling the template with context data.
        
        Args:
            context_data (dict): A dictionary containing all the text parts 
                                 to fill the template's placeholders.
        """
        try:
            return self.template.format(**context_data)
        except KeyError as e:
            raise KeyError(f"The placeholder {e} in the template was not found in the provided context data.")