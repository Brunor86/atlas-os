import requests


class PrometheusClient:


    def __init__(
        self,
        url="http://localhost:9090"
    ):

        self.url = url



    def query(self, expression):

        response = requests.get(

            f"{self.url}/api/v1/query",

            params={
                "query": expression
            },

            timeout=5

        )


        response.raise_for_status()


        data = response.json()


        return (
            data
            .get("data", {})
            .get("result", [])
        )
