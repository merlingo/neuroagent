def has_required_variables(template: str, variables: list[str]) -> bool:
    return all("{" + variable + "}" in template for variable in variables)
