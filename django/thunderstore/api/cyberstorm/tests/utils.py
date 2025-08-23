import re

from jsonschema import RefResolver, ValidationError, validate


def convert_x_nullable(schema: dict) -> dict:
    if isinstance(schema, dict):
        if schema.get("x-nullable") is True:
            type_ = schema.get("type")
            if type_:
                if isinstance(type_, str):
                    schema["type"] = [type_, "null"]
                elif isinstance(type_, list) and "null" not in type_:
                    schema["type"].append("null")
            schema.pop("x-nullable")

        for key in schema:
            schema[key] = convert_x_nullable(schema[key])

    return schema


def get_response_schema(schema: dict, path: str, method: str):
    status_codes = [200, 201, 202, 204]

    responses = (
        schema.get("paths", {})
        .get(path, {})
        .get(method.lower(), {})
        .get("responses", {})
    )

    for code in status_codes:
        response_schema = responses.get(str(code), {}).get("schema")
        if response_schema:
            return convert_x_nullable(response_schema)

    return {}


def get_request_body_schema(schema: dict, path: str, method: str):
    request_body_schema = (
        schema.get("paths", {})
        .get(path, {})
        .get(method.lower(), {})
        .get("parameters", [])
    )

    for param in request_body_schema:
        if param.get("in") == "body":
            return convert_x_nullable(param.get("schema", {}))

    return {}


def get_resolver(schema: dict) -> RefResolver:
    definitions = schema.get("definitions", {})
    if not definitions:
        raise ValueError("Schema does not contain definitions.")
    definitions = convert_x_nullable(definitions)
    return RefResolver.from_schema({"definitions": definitions})


def get_schema(api_client) -> dict:
    response = api_client.get("/api/docs/?format=openapi")
    schema = response.json()
    return schema


def extract_paths(schema: dict, api_name: str, http_verb: str = None) -> list:
    url_paths = []
    all_paths = schema.get("paths", {}).items()

    if http_verb is None:
        for path, methods in all_paths:
            if api_name in path:
                url_paths.append(path)
        return url_paths
    else:
        http_verb = http_verb.lower()

    for path, methods in all_paths:
        if api_name in path and http_verb in methods:
            url_paths.append(path)

    return url_paths


def fill_path_params(path: str, param_values: dict) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(param_values.get(m.group(1), "1")), path)


def convert_path_to_schema_style(path: str) -> str:
    return re.sub(r"<\w+:(\w+)>", r"{\1}", str(path))


def validate_response_against_schema(
    response,
    path: str,
    method: str,
    schema: dict,
    resolver: RefResolver,
) -> list:
    errors = []

    success_statuses = [200, 201, 202, 204]

    if response.status_code not in success_statuses:
        try:
            data = response.json()
        except Exception:
            if hasattr(response, "text"):
                data = response.text
            else:
                data = "No response body. Check content-type."
        errors.append(f"Unexpected status {response.status_code} for {path}: {data}")
        return errors

    if response.status_code == 204:
        return []

    res_schema = get_response_schema(schema, path, method)

    try:
        response_data = response.json()
        validate(instance=response_data, schema=res_schema, resolver=resolver)
    except ValidationError as e:
        error_message = f"Validation error for [{method.upper()}], {path}: {e.message}"
        field_path = ".".join(str(x) for x in e.path)
        if field_path:
            error_message += f", field: {field_path}"
        errors.append(error_message)

    return errors


def validate_request_body_against_schema(
    request_body: dict,
    path: str,
    method: str,
    schema: dict,
    resolver: RefResolver,
) -> list:
    errors = []

    req_schema = get_request_body_schema(schema, path, method)
    if not req_schema:
        errors.append(f"No request body schema found for {path}")
        return errors

    try:
        validate(instance=request_body, schema=req_schema, resolver=resolver)
    except ValidationError as e:
        error_message = f"Validation error for [{method.upper()}], {path}: {e.message}"
        field_path = ".".join(str(x) for x in e.path)
        if field_path:
            error_message += f", field: {field_path}"
        errors.append(error_message)

    return errors
