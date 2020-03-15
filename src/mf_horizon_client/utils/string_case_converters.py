import re
from typing import Any, Dict


def force_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def force_snake_case(string: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", string).lower()


def convert_dict_from_snake_to_camel(snake_dict: Dict[str, Any]) -> Dict[str, Any]:
    camel_dict = {}
    for key, value in snake_dict.items():
        camel_dict[force_camel_case(key)] = value

    return camel_dict


def convert_dict_from_camel_to_snake(camel_dict: Dict[str, Any]) -> Dict[str, Any]:
    snake_dict = {}
    for key, value in camel_dict.items():
        if key == "id":
            snake_dict["id_"] = value
        else:
            snake_dict[force_snake_case(key)] = value
    return snake_dict
