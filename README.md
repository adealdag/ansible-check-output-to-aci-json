# Ansible Check Output to ACI json config

This python script transforms the file that is created after running Cisco ACI ansible modules with the flag `--check` and output_path attribute set into a correctly structured Cisco ACI config.

The output of Cisco ACI ansible modules support a dryrun option where nothing is pushed to Cisco ACI but configuration in JSON is pushed into a file. This is done by:

* Setting the attribute `output_path` in all tasks
* Running the playbook with flag `--check`

However, the output is not a valid Cisco ACI config (it is not a tree of objects but a list of individual object configurations). This script transforms the `output_path` file into a valid Cisco ACI configuration tree.

This script is taken from the former NAE ansible module that creates pre-change validations from a file. In this case, the part of the code that transform the configuration into a tree has been taken out into an independent script.

## How to run

```
config_construct_tree(input_file, output_file)
```
