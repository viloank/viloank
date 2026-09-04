from ansible.plugins.lookup import LookupBase
from ansible.errors import AnsibleLookupError
from ansible.utils.display import Display
from ansible.module_utils.urls import open_url
from ansible.module_utils._text import to_native
import json
import os

display = Display()


class LookupModule(LookupBase):

    def tower_api(self, url, token):

        display.display("")
        display.display("===== RAF Lookup Plugin =====")
        display.display("GET {}".format(url))

        try:
            response = open_url(
                url,
                headers={
                    "Authorization": "Bearer {}".format(tower_token)
                },
                validate_certs=False
            )

            return json.loads(response.read().decode())

        except Exception as e:
            raise AnsibleLookupError(
                "Tower API call failed: {}".format(to_native(e))
            )

    def run(self, terms=None, variables=None, **kwargs):

        ####################################################
        # Read environment variables
        ####################################################

        tower_host = os.environ.get(
            "TOWER_HOST",
            "http://13.204.249.230:31454"          #
        ).rstrip("/")

        tower_token = os.environ.get(
            "TOWER_OAUTH_TOKEN",
            "XiCosswuvm2iX4j0hSRX9H2VtYoLHb"            #
        )

        api_path = os.environ.get(
            "CONTROLLER_API_PATH",
            "api/v2"
        ).strip("/")

        inventory_id = str(
            variables.get("awx_inventory_id", "2")
        )

        ####################################################
        # Read search values
        ####################################################

        hostname = variables.get("hostname", "")
        fqdn = variables.get("fqdn", "")
        ipaddress = variables.get("ipaddress", "")

        display.display("")
        display.display("===== RAF Configuration =====")
        display.display("Tower Host  : {}".format(tower_host))
        display.display("Inventory  : {}".format(inventory_id))
        display.display("Hostname   : {}".format(hostname))
        display.display("FQDN       : {}".format(fqdn))
        display.display("IP Address : {}".format(ipaddress))

        ####################################################
        # Search order
        ####################################################

        search_values = []

        if hostname:
            search_values.append(hostname)

        if fqdn:
            search_values.append(fqdn)

        if ipaddress:
            search_values.append(ipaddress)

        ####################################################
        # Search host
        ####################################################

        for value in search_values:

            url = (
                f"{tower_host}/{api_path}"
                f"/inventories/{inventory_id}"
                f"/hosts/?enabled=true&name__iexact={value}"
            )

            js = self.tower_api(url, tower_token)

            display.display(
                "Search '{}' returned {} host(s)".format(
                    value,
                    js["count"]
                )
            )

            if js["count"] == 1:

                host = js["results"][0]

                display.display("")
                display.display("Host Found!")
                display.display("Host Name : {}".format(host["name"]))
                display.display("Host ID   : {}".format(host["id"]))

                return [dict(
                    host_found=True,
                    found_duplicates=False,
                    exclude_group=False,
                    host_name=host["name"],
                    host_enabled=host["enabled"],
                    error=False
                )]

            elif js["count"] > 1:

                duplicates = [
                    h["name"] for h in js["results"]
                ]

                display.display(
                    "Duplicate hosts found: {}".format(
                        duplicates
                    )
                )

                return [dict(
                    host_found=True,
                    found_duplicates=True,
                    duplicate_hosts=duplicates,
                    error=False
                )]

        ####################################################
        # Not found
        ####################################################

        display.display("")
        display.display("Host NOT found")

        return [dict(
            host_found=False,
            found_duplicates=False,
            exclude_group=False,
            error=False
        )]
