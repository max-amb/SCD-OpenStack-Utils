#!/usr/bin/env python3
from typing import List, Dict
from datetime import datetime
import json
import socket
import requests


class RawData:
    """
    This class gets the raw JSON data from the Prometheus endpoint and writes that to files.
    """

    def __init__(self, metrics: List[str], start: str, end: str, url: str):
        self.metrics = metrics
        self.start = start
        self.end = end
        self.step = 60
        self.endpoint = url

    def request_to_json_file(self):
        """
        This method runs the request and write function for each metric you want to query for.
        It will write into CSV files called the metrics name.
        """
        for metric in self.metrics:
            payload = {
                "query": metric,
                "start": self.start,
                "end": self.end,
                "step": self.step,
            }
            response = self.http_request(payload)
            self.write_json_file(metric, response)

    def http_request(self, metric) -> requests.Response:
        """
        This method uses the request library's get function to send a HTTP GET request to the endpoint.
        :param metric: The metric to query for
        :return: The HTTP response
        """
        response = requests.get(self.endpoint, params=metric, timeout=300)
        assert response.status_code == 200, "The HTTP response did not return okay."
        return response

    @staticmethod
    def write_json_file(name: str, response: requests.Response):
        """
        This method writes the response data to a file.
        :param name: The metric name
        :param response: The HTTP response
        """
        with open(f"{name}.csv", "w", encoding="utf-8") as json_file:
            data = response.json()
            json_file.write(str(data))


class JsonToCSV:
    """
    This class trims the raw JSON data to a CSV format file.
    """

    def __init__(self, metrics: List[str]):
        self.metrics = metrics

    def json_to_csv(self):
        """
        This method reads a file and calls the format function for each file.
        Then writes the newly formatted data to that original file.
        """
        for metric in self.metrics:
            json_data = self.read_json(metric)
            dictionary = self.json_to_dict(json_data)
            self.dict_to_csv(dictionary)

    @staticmethod
    def read_json(file_name: str) -> str:
        """
        This method reads the data in to Python from the file.
        :param file_name: The file name to read
        :return: Returns the data read from the file
        """
        with open(f"{file_name}.csv", "r", encoding="utf-8") as json_file:
            json_data = json_file.read()
            return json_data

    @staticmethod
    def json_to_dict(data: str) -> Dict:
        """
        This method converts the read string into a Python dictionary.
        :param data: The data read from the file
        :return: Returns the data as a dictionary
        """
        data = data.replace("'", '"')
        json_data = json.loads(data)
        return json_data

    def dict_to_csv(self, json_data: Dict):
        """
        This method writes the data into a CSV file formatted using f strings to only write the data we want.
        :param json_data: The data from the file in a dictionary
        """
        data = json_data["data"]["result"]
        try:
            metric_type = data[0]["metric"]["__name__"]
        except IndexError as exc:
            raise Exception(
                "Your query returned no data. "
                "Check that there is data in the time range then try decreasing the step to query at shorter intervals."
            ) from exc
        if metric_type.startswith("openstack"):
            self.dict_to_csv_openstack(data)
        elif metric_type.startswith("node"):
            self.dict_to_csv_node(data)
        else:
            raise Exception(
                "Unsupported query type: openstack or node currently supported."
            )

    @staticmethod
    def dict_to_csv_openstack(data: Dict):
        """
        This method supports "openstack" queries.
        """
        file_name = data[0]["metric"]["__name__"] + ".csv"
        with open(file_name, "w", encoding="utf-8") as csv_file:
            line = f'Date Time Hostname {data[0]["metric"]["__name__"]}\n'
            csv_file.write(line)
            for metric in data:
                for i in range(len(metric["values"]) - 1):
                    time = datetime.fromtimestamp(metric["values"][i][0])
                    hostname = metric["metric"]["hostname"]
                    value = metric["values"][i][1]
                    line = f"{time} {hostname} {value}\n"
                    csv_file.write(line)

    @staticmethod
    def dict_to_csv_node(data: Dict):
        """
        This method supports "node" queries.
        """
        file_name = data[0]["metric"]["__name__"] + ".csv"
        with open(file_name, "w", encoding="utf-8") as csv_file:
            line = f'Date Time Hostname {data[0]["metric"]["__name__"]}\n'
            csv_file.write(line)
            for metric in data:
                for i in range(len(metric["values"]) - 1):
                    time = datetime.fromtimestamp(metric["values"][i][0])
                    hostname = socket.gethostbyaddr(
                        metric["metric"]["instance"].split(":")[0]
                    )[0]
                    value = metric["values"][i][1]
                    line = f"{time} {hostname} {value}\n"
                    csv_file.write(line)


if __name__ == "__main__":
    # Example metrics to query for
    metrics_to_query = [
        "openstack_nova_vcpus_used",
        "openstack_nova_memory_used_bytes",
        "node_hwmon_power_average_watt",
    ]
    # Prometheus host api endpoint
    ENDPOINT = "http://172.16.102.82:9090/api/v1/query_range"
    # Start and end time as posix seconds - this represents x date and y date
    START_TIME = "1710770960"
    END_TIME = "1710857376"
    RawData(metrics_to_query, START_TIME, END_TIME, ENDPOINT).request_to_json_file()
    JsonToCSV(metrics_to_query).json_to_csv()
