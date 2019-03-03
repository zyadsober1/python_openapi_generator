import yaml
import urllib
import json


class OpenapiGenerator():
    types_map = {"int": "integer",
                 "bool": "boolean",
                 "float": "number",
                 "str": "string",
                 "list": "array",
                 "dict": "object"}

    def __init__(self, title, description, version, server):
        self.configs = {
            "openapi": "3.0.1",
            "info": {"title": title, "description": description, "version": version},
            "servers": [
                {"url": server, "description": "Path to server"}
            ]
        }
        self.paths = {}

    def add_response(self, response, description=""):
        path_object = {}
        parameters = self._get_parameters(response)
        request_body = self._get_request_body(response)
        responses = self._get_response(response)

        if description:
            path_object['description'] = description

        if parameters:
            path_object['parameters'] = parameters

        if request_body:
            path_object['requestBody'] = request_body

        if responses:
            path_object['responses'] = responses

        parsed_url = urllib.parse.urlparse(response.request.url)
        if parsed_url.path in self.paths:
            if "responses" in self.paths[parsed_url.path]:
                k = list(path_object["responses"].keys())[0]
                self.paths[parsed_url.path]["responses"][k] = path_object["responses"][k]
            else:
                self.paths[parsed_url.path]["responses"] = path_object["responses"]

            if description:
                self.paths[parsed_url.path]["description"] = description
        else:
            self.paths[parsed_url.path] = {response.request.method.lower(): path_object}
        self.configs["paths"] = self.paths

    def export(self, filename):
        with open(filename, "w") as output_file:
            output_file.write(yaml.dump(self.configs, default_flow_style=False))

    @staticmethod
    def _get_request_body(response):
        request_body = {}
        if response.request.body:
            if response.request.headers['Content-Type'] == 'application/json':
                try:
                    example = json.loads(response.request.body.decode('utf-8'))
                    request_body['content'] = {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    k: {'type': OpenapiGenerator.types_map[v.__class__.__name__]}
                                    for k, v in example.items()}
                            },
                            'example': {k: v for k, v in example.items()}
                        }
                    }
                except ValueError:
                    print("invalid json passed")

        return request_body

    @staticmethod
    def _get_response(response):
        status = "{}".format(response.status_code)
        return {
            status: {
                'description': 'Get this from docstring',
                'content': {
                    response.headers['Content-Type']: {
                        'schema': {
                            'type': 'object',
                            'properties': {
                                k: {'type': OpenapiGenerator.types_map[v.__class__.__name__]}
                                for k, v in response.json().items()}
                        },
                        'example': {k: v for k, v in response.json().items()}
                    }
                }
            }
        }

    @staticmethod
    def _get_parameters(response):
        # Adding parameters [query, headers, cookie].
        # TODO: implement [path] parameters.
        parameters = []

        def create_param_dict(k, v, param_type):
            return {
                'name': k,
                'in': param_type,
                'schema': {'type': OpenapiGenerator.types_map[v.__class__.__name__]},
                'example': v
            }

        qs = urllib.parse.parse_qs(urllib.parse.urlparse(response.request.url).query)
        for k, v in qs.items():
            parameters.append(create_param_dict(k, v[0], 'query'))

        for k, v in response.request.headers.items():
            if k in ['Accept', 'Connection', 'User-Agent', 'Accept-Encoding', 'Content-Length']:
                continue
            parameters.append(create_param_dict(k, v, 'header'))

        for k, v in response.cookies.items():
            parameters.append(create_param_dict(k, v, 'cookie'))

        return parameters
