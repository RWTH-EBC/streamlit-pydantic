"""Utilities to help with JSON Schema.

lazydocs: ignore
"""
import logging
from typing import Dict, List


def resolve_reference(reference: str, references: Dict) -> Dict:
    return references[reference.split("/")[-1]]


def get_single_reference_item(property: Dict, references: Dict) -> Dict:
    # Ref can either be directly in the properties or the first element of allOf
    reference = property.get("$ref")
    if reference is None:
        reference = property["allOf"][0]["$ref"]
    return resolve_reference(reference, references)


def get_union_references(property: Dict, references: Dict) -> List[Dict]:
    # Ref can either be directly in the properties or the first element of allOf
    # anyOf is used for union property prior to pydantic < 1.10
    union_references = property.get("oneOf", property.get("anyOf"))
    resolved_references: List[Dict] = []
    for reference in union_references:  # type: ignore
        resolved_references.append(resolve_reference(reference["$ref"], references))
    return resolved_references


def is_single_string_property(property: Dict) -> bool:
    return property.get("type") == "string"


def is_single_color_property(property: Dict) -> bool:
    if property.get("type") != "string":
        return False
    return property.get("format") in ["color"]


def is_single_datetime_property(property: Dict) -> bool:
    if property.get("type") != "string":
        return False
    return property.get("format") in ["date-time", "time", "date"]


def is_single_boolean_property(property: Dict) -> bool:
    return property.get("type") == "boolean"


def is_single_number_property(property: Dict) -> bool:
    return property.get("type") in ["integer", "number"]


def is_single_file_property(property: Dict) -> bool:
    if property.get("type") != "string":
        return False
    # TODO: binary?
    return property.get("format") == "byte"


def is_multi_enum_property(property: Dict, references: Dict) -> bool:
    if property.get("type") != "array":
        return False

    if property.get("uniqueItems") is not True:
        # Only relevant if it is a set or other datastructures with unique items
        return False

    try:
        # Uses literal
        _ = get_property_items(property)["enum"]
        return True
    except Exception:
        pass

    try:
        # Uses enum
        _ = resolve_reference(get_property_items(property)["$ref"], references)["enum"]
        return True
    except Exception:
        return False


def is_single_enum_property(property: Dict, references: Dict) -> bool:
    if property.get("enum"):
        return True

    try:
        _ = get_single_reference_item(property, references)["enum"]
        return True
    except Exception:
        return False


def is_single_dict_property(property: Dict) -> bool:
    if property.get("type") != "object":
        return False
    return "additionalProperties" in property


def is_single_reference(property: Dict) -> bool:
    if property.get("type") is not None:
        return False

    return bool(property.get("$ref"))


def is_multi_file_property(property: Dict) -> bool:
    if property.get("type") != "array":
        return False

    if property.get("items") is None:
        return False

    try:
        # TODO: binary
        return get_property_items(property)["format"] == "byte"
    except Exception:
        return False


def is_single_object(property: Dict, references: Dict) -> bool:
    try:
        object_reference = get_single_reference_item(property, references)
        if object_reference["type"] != "object":
            return False
        return "properties" in object_reference
    except Exception:
        return False


def is_union_property(property: Dict) -> bool:
    # anyOf is used for union property prior to pydantic < 1.10
    union_prop = property.get("oneOf", property.get("anyOf"))

    if union_prop is None:
        return False

    if len(union_prop) == 0:  # type: ignore
        return False

    for reference in union_prop:  # type: ignore
        if not is_single_reference(reference):
            return False

    return True


def is_property_list_and_object(property: Dict, references) -> bool:
    if property.get("type") != "array":
        return False

    if property.get("items") is None and property.get("anyOf", [{}])[0].get("items") is None:
        return False

    try:
        item_property = get_property_items(property)
    except (KeyError, TypeError):
        item_property = get_property_items(property.get("anyOf")[0])

    # Check if it is an object
    if "$ref" in item_property:
        object_reference = resolve_reference(item_property["$ref"], references)
        if object_reference["type"] in ["string", "number", "integer"]:
            item_property.pop("$ref")
            item_property["type"] = object_reference["type"]
        elif object_reference["type"] != "object":
            raise TypeError(f"Type of array-like field not supported: {object_reference['type']}")
        else:
            property["items"] = item_property
            return "properties" in object_reference
    if item_property.get("type") in ["string", "number", "integer"]:
        property["items"] = item_property
        return True
    return False


def get_property_items(property):
    if isinstance(property["items"], list):
        return property["items"][0]
    if isinstance(property["items"], dict):
        return property["items"]
    raise TypeError(f"Given type of items is not supported: {property['items']}")
