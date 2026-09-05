#!/usr/bin/python

# Copyright: (c) 2020, Pavel Jedlicka <pavel_jedlicka@cz.ibm.com>
# IBM internal usage

# version 0.1 - 2020-03-10 - initial version
# version 0.2 - 2020-03-17 - added handling exception if expression key is missing
# version 20.5.0 - 2020-05-15 - Initial release to match Next versioning
# changes: - merging internat test matchers
#          - making custom_playbook default value to False
# version 20.5.1 - 2020-06-04 - Enhancing matching capabilities
# version 20.5.2 - 2020-06-04 - Optimizing plugin
# changes: - remove recursive vars loopup
#          - Templar to use only selected vars
# version 20.5.3 - 2020-06-24 - Adding Sender_ID and Service_Type vars
# changes: - no changes in this plugin
# version 20.5.4 - 2020-07-20 - Adding exception handlers
# changes: - catch no matchers found
#          - catch matcher corrupted
# version 20.5.6 - 2020-11-20 - SienceLogic update
# changes: no changes in the module
# version 21.2.0 - 2020-01-01 - Skip precheck
# changes: - to work with additional param `skip_precheck`
#          - change versioning to match NEXT releases


# action plugin for Ansible 2.x
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError, AnsibleFileNotFound, AnsibleAction, AnsibleActionFail, AnsibleUndefinedVariable
from ansible.module_utils._text import to_bytes, to_text, to_native
from ansible.utils.vars import merge_hash
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.template import Templar
from ansible.utils.display import Display
import yaml
import re

display = Display()

class ActionModule(ActionBase):

    def _get_test_config(self, load_from='files',
                     config_file='matcher_config.yml',
                     tmp=None,
                     task_vars=None):

      display.display("Searching for matcher_config.yml")

      try:
        path = self._find_needle(load_from, config_file)
        display.display("FOUND: {}".format(path))
        return self._loader.get_real_file(path)

      except Exception as e:
        display.display("ERROR FINDING FILE")
        display.display(str(e))
        raise

    def _is_rule_enabled(self, rule):
        if rule['enabled']:
            return True
        else:
            return False

    def _findvar(self, vars, key):
        for k, v in vars.items():
            if k == key and vars[key] is not None:
                return vars[key]

    def _eval_matcher_expression(self, expr, vars):

        def _eval_value(i, k):
            isneg = None
            matchvar = None
            isneg = re.match(r'^not\s+.*$', i, re.I)
            if isneg:
                i = re.sub(r'(?i)^not\s+', '', i)
            mreg = re.compile(i)
            try:
                matchvar = mreg.match(self._findvar(vars=vars, key=k))
            except Exception as e:
                display.v("Error: " + to_text(e))
                display.v("Key '%s' is not defined" % to_text(k))
            if isneg and not matchvar: return True
            if not isneg and matchvar: return True
            return False

        _total = 0
        isneg = None
        if isinstance(expr, dict):
            for k, v in expr.items():
                if isinstance(v, list):
                    _itotal = 0
                    for i in v:
                        if _eval_value(i, k): _itotal += 1
                    if _itotal >= len(v): _total += 1
                else:
                    if _eval_value(v, k): _total += 1

        return _total >= len(expr.keys()) or False


    def run(self, tmp=None, task_vars=None):

        display.display("******** EVENT MAPPER RUNNING ********")
        result = super(ActionModule, self).run(tmp, task_vars)

        # Load job variables
        temp_vars = task_vars.copy()
        display.display("========== EVENT MAPPER INPUT ==========")

        for key in [
           "classification",
           "item",
           "itemcode",
           "affected_host",
           "ipaddress",
           "sr_data",
           "matchers",
           "em_vars_to_template"
        ]:
           display.display("{} = {}".format(key, temp_vars.get(key)))
        
        data_loader = DataLoader()

        vars_to_template = {k: temp_vars[k] for k in temp_vars['em_vars_to_template']}

        templar = Templar(data_loader, variables=temp_vars)

        try:
            temp_vars = merge_hash(
                temp_vars,
                templar.template(vars_to_template, fail_on_undefined=False)
            )

        except Exception as e:
            display.v(to_text(e))
            pass

        # check if temp_vars['matchers'] exist
        if 'matchers' not in temp_vars or\
        not isinstance(temp_vars['matchers'], list):
            result['changed'] = False
            result['failed'] = True
            result['msg'] = "No matchers found. Check the 'mapper_config.yml'" \
                            " is configured and present in the repository."
            return result

        # collect only enabled rules
        matchers = list(filter(self._is_rule_enabled,temp_vars['matchers']))

        matcher_config_file = self._get_test_config(load_from='files',
                                                    config_file='matcher_config.yml',
                                                    task_vars=temp_vars)
        display.display("")
        display.display("===== Event Mapper Debug =====")
        display.display("matcher_config_file = {}".format(matcher_config_file))
        
        try:
            with open(matcher_config_file) as mcf:
                content = mcf.read()
            matcher_config_tests = yaml.safe_load(content)
        except:
            display.vvvv("Cannot add test matchers.")
            pass

        # if matcher_config_tests correct, include the test expressions in matchers
        if matcher_config_tests and 'matchers' in matcher_config_tests:
            for m in matchers:
                for n in matcher_config_tests['matchers']:
                    if m['name'] == n['name']:
                        # found the matcher, include expression from test matchers
                        m['matcher_expressions'].extend(n['matcher_expressions'])
                        continue
        else:
            display.v("Config file %s is missing or incorrect format." % matcher_config_file)

        found_matcher = None

        if not isinstance(matchers, list):
            result['changed'] = False
            result['failed'] = True
            result['msg'] = "Matchers format is not correct. Check if the " \
                            "variable 'matchers' contains a list of matchers."
            return result
            
        display.display("===== MATCHERS =====")
        display.display(matchers)

        for matcher in matchers:

            if 'matcher_expressions' not in matcher or\
            not isinstance(matcher['matcher_expressions'], list):
                display.v("Matcher '%s' does not have any valid expressions.\
                           Skipping." % matcher_config_file)
                continue

            for e in matcher['matcher_expressions']:
                display.display("---------------------")
                display.display("Matcher : {}".format(matcher["name"]))
                display.display("Expression : {}".format(e))

                result_eval = self._eval_matcher_expression(expr=e, vars=temp_vars)

                display.display("Matched : {}".format(result_eval))

                if result_eval:
                   found_matcher = matcher
                   break
                    
            if found_matcher:
                break

        if found_matcher is not None:

            set_fact_args = {}
            set_fact_args['common_role_name'] = found_matcher['name']
            if 'custom_playbook' in found_matcher:
                set_fact_args['custom_playbook'] = found_matcher['custom_playbook']
            else:
                set_fact_args['custom_playbook'] = False
            if 'skip_precheck' in found_matcher and found_matcher['skip_precheck']:
                set_fact_args['skip_precheck'] = True
            else:
                set_fact_args['skip_precheck'] = False
            result['matched'] = set_fact_args

        else:
            result['changed'] = False
            result['failed'] = False
            result['msg'] = "No matching mappers."

        return result
