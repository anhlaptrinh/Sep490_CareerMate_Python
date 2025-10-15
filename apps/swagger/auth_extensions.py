from drf_spectacular.extensions  import OpenApiAuthenticationExtension


class BearerAuthScheme(OpenApiAuthenticationExtension):
    target_class = 'apps.swagger.authentication.BearerAuthentication'
    name = 'bearerAuth'

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }