from ansible.errors import AnsibleLookupError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible.module_utils._text import to_native, to_text
from ansible.module_utils.urls import open_url
import os

import json
from re import compile as regex_compile

display = Display()

class LookupModule(LookupBase):
    def call_tower_api(self, url, token):
      try:
        response = open_url(
                  url,
                  headers = {'Authorization': 'Bearer ' + token},
                  validate_certs=False
              )
      except Exception as e:
        results.append(dict(host_found=False, exclude_group='', found_duplicates=False, error=True, error_message=to_native(e)))
        return results
      return response

    def run(self, hosts=None, variables=None, **kwargs):
        global results 
        results = []
        results_dict = {}
        results_dict['host_found']=False
        exact_match=['hostname', 'fqdn','ipaddress']
        shortname_match=['hostname','fqdn']
        #resource_node_match=['resource_id', 'node']
        try:
          tower_token=os.environ['TOWER_OAUTH_TOKEN']
          tower_host=os.environ['TOWER_HOST']
          api_path=os.environ.get('CONTROLLER_API_PATH', 'api/v2').strip('/')
          inv_id=str(variables['awx_inventory_id'])
          global_shortcode=str(variables['org_code']).lower()
        except Exception as e:
          results_dict.update({'host_found':False, 'exclude_group':'', 'found_duplicates':False, 'error':True, 'error_message': to_native(e)+" not defined"})
          results.append(results_dict)
          return results

        req_vars=['tower_token', 'tower_host', 'global_shortcode','inv_id']
        for var in req_vars:
            if not eval(var):
              results_dict.update({'host_found':False, 'exclude_group':'', 'found_duplicates':False, 'error':True, 'error_message': var+" not defined"})
              results.append(results_dict)
              return results

        #Remove trailing backslash from url
        tower_host="https://"+tower_host.split("//")[-1].split("/")[0].split('?')[0]
        found_duplicates, duplicated_hosts = False, []

        #Exact match search
        host_found=False
        for f in exact_match:
         host=variables[f]
         if host and host_found == False:
           search_url=tower_host+"/"+api_path+"/inventories/"+inv_id+"/hosts/?enabled=true&name__iexact="+host
           response=self.call_tower_api(search_url, tower_token)
           if (type(response)) == list:
              return results
           try:
             js_out=json.loads(response.read().decode("utf-8"))
             if js_out['count'] > 1:
                found_duplicates=True
                for h in js_out['results']:
                   duplicated_hosts.append(h['name']) if h['name'] not in duplicated_hosts else duplicated_hosts
             if js_out['count'] == 1:
               host_found=True
               search_url=tower_host+"/"+api_path+"/inventories/"+inv_id+"/hosts/?enabled=true&groups__name__icontains=_blacklist_&name__iexact="+js_out['results'][0]['name']
               response1=self.call_tower_api(search_url, tower_token)
               js_out1=json.loads(response1.read().decode("utf-8"))
               if js_out1['count'] > 0:
                 results.append(dict(found_duplicates=False, host_found=True, host_name=js_out['results'][0]['name'], host_enabled=js_out['results'][0]['enabled'], exclude_group=True, error=False))
               else:
                 results.append(dict(found_duplicates=False, host_found=True, host_name=js_out['results'][0]['name'], host_enabled=js_out['results'][0]['enabled'], exclude_group=False, error=False)) 
               return results
           except ValueError or JSONDecodeError or KeyError as e:
             raise AnsibleLookupError("Error parsing JSON from tower API response: %s" % to_native(e))

        #Shortname iexact match
        for f in shortname_match:
         host=variables[f]
         host_shortname=host.split(".")[0]
         if host and host_shortname and host_found == False:
           search_url=tower_host+"/"+api_path+"/inventories/"+inv_id+"/hosts/?enabled=true&name__iexact="+host_shortname
           response=self.call_tower_api(search_url, tower_token)
           if (type(response)) == list:
              return results
           try:
             js_out=json.loads(response.read().decode("utf-8"))
             if js_out['count'] > 1:
                found_duplicates=True
                for h in js_out['results']:
                   duplicated_hosts.append(h['name']) if h['name'] not in duplicated_hosts else duplicated_hosts
                              
             if js_out['count'] == 1:
               host_found=True
               search_url=tower_host+"/"+api_path+"/inventories/"+inv_id+"/hosts/?enabled=true&groups__name__icontains=_blacklist_&name__iexact="+js_out['results'][0]['name']
               response1=self.call_tower_api(search_url, tower_token)
               js_out1=json.loads(response1.read().decode("utf-8"))
               if js_out1['count'] > 0:
                 results.append(dict(found_duplicates=False, host_found=True, host_name=js_out['results'][0]['name'], host_enabled=js_out['results'][0]['enabled'], exclude_group=True, error=False))
               else:
                 results.append(dict(found_duplicates=False, host_found=True, host_name=js_out['results'][0]['name'], host_enabled=js_out['results'][0]['enabled'], exclude_group=False, error=False))
               return results
           except ValueError or JSONDecodeError or KeyError as e:
             raise AnsibleLookupError("Error parsing JSON from tower API response: %s" % to_native(e))                    

        #Shortname istartswith match
        for f in shortname_match:
         host=variables[f]
         host_shortname=host.split(".")[0]
         if host and host_shortname and host_found == False:
           search_url=tower_host+"/"+api_path+"/inventories/"+inv_id+"/hosts/?enabled=true&name__istartswith="+host_shortname+"."
           response=self.call_tower_api(search_url, tower_token)
           if (type(response)) == list:
              return results
           try:
             js_out=json.loads(response.read().decode("utf-8"))
             if js_out['count'] > 1:
                found_duplicates=True
                for h in js_out['results']:
                   duplicated_hosts.append(h['name']) if h['name'] not in duplicated_hosts else duplicated_hosts
                              
             if js_out['count'] == 1:
               host_found=True
               search_url=tower_host+"/"+api_path+"/inventories/"+inv_id+"/hosts/?enabled=true&groups__name__icontains=_blacklist_&name__iexact="+js_out['results'][0]['name']
               response1=self.call_tower_api(search_url, tower_token)
               js_out1=json.loads(response1.read().decode("utf-8"))
               if js_out1['count'] > 0:
                 results.append(dict(found_duplicates=False, host_found=True, host_name=js_out['results'][0]['name'], host_enabled=js_out['results'][0]['enabled'], exclude_group=True, error=False))
               else:
                 results.append(dict(found_duplicates=False, host_found=True, host_name=js_out['results'][0]['name'], host_enabled=js_out['results'][0]['enabled'], exclude_group=False, error=False))
               return results
           except ValueError or JSONDecodeError or KeyError as e:
             raise AnsibleLookupError("Error parsing JSON from tower API response: %s" % to_native(e))                    

        if host_found == False and found_duplicates == False:
           results.append(dict(found_duplicates=False, host_found=False, exclude_group=False, error=False))          
           return results
        else:
           results.append(dict(found_duplicates=True, host_found=True, duplicate_hosts=duplicated_hosts, error=False))          
           return results
