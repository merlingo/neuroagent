def render(template: str, variables: dict[str, object]) -> str:
    return template.format(**variables)
