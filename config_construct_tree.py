import os
import logging
import json
from jsonpath_ng import parse


def config_construct_tree(input_file, output_file):

    # Validate inputs
    if not os.path.exists(input_file):
        logging.error("File not found : {0}".format(input_file))

    with open(input_file, "rb") as f:
        if is_json(f.read()) is False:
            with open(input_file) as fh:
                data = load(fh)
                tree, cmap = construct_tree(data)
                create_structured_data(tree, cmap, output_file)
        else:
            try:
                f.seek(0)
                extract_data = json.loads(f.read())
                tree, cmap = construct_tree([extract_data[0]])
                create_structured_data(tree, cmap, output_file)
            except KeyError:
                pass
    return


def is_json(myjson):
    try:
        json.loads(myjson)
    except ValueError:
        return False
    return True


def load(fh, chunk_size=1024):
    depth = 0
    in_str = False
    items = []
    buffer = ""

    while True:
        chunk = fh.read(chunk_size)
        if len(chunk) == 0:
            break
        i = 0
        while i < len(chunk):
            c = chunk[i]
            # if i == 0 and c != '[':
            # self.module.fail_json(msg="Input file invalid or already parsed.", **self.result)
            buffer += c

            if c == '"':
                in_str = not in_str
            elif c == '[':
                if not in_str:
                    depth += 1
            elif c == ']':
                if not in_str:
                    depth -= 1
            elif c == '\\':
                buffer += c[i + 1]
                i += 1

            if depth == 0:
                if len(buffer.strip()) > 0:
                    j = json.loads(buffer)
                    if not isinstance(j, list):
                        raise AssertionError("")
                    items += j
                buffer = ""

            i += 1

    if depth != 0:
        raise AssertionError("Error in loading input json")
    return items


def construct_tree(item_list):
    """
    Given a flat list of items, each with a dn. Construct a tree represeting their relative relationships.
    E.g. Given [/a/b/c/d, /a/b, /a/b/c/e, /a/f, /z], the function will construct
    __root__
        - a (no data)
            - b (data of /a/b)
            - c (no data)
                - d (data of /a/b/c/d)
                - e (data of /a/b/c/e)
            - f (data of /a/f)
        - z (data of /z)
    __root__ is a predefined name, you could replace this with a flag root:True/False
    """
    cmap = {}
    tree = {'data': None, 'name': '__root__', 'children': {}}

    for item in item_list:
        for nm, desc in item.items():
            if 'attributes' not in desc:
                raise AssertionError("attributes not in desc")
            attr = desc.get('attributes')
            if 'dn' not in attr:
                raise AssertionError("dn not in desc")
            if 'children' in desc:
                existing_children = desc.get('children')
                cmap[attr['dn']] = existing_children
            path = parse_path(attr['dn'])
            cursor = tree
            curr_node_dn = ""
            for node in path:
                curr_node_dn += "/" + str(node)
                if curr_node_dn[0] == "/":
                    curr_node_dn = curr_node_dn[1:]
                if node not in cursor['children']:
                    if node == 'uni':
                        cursor['children'][node] = {
                            'data': None,
                            'name': node,
                            'children': {}
                        }
                    else:
                        aci_class_identifier = node.split("-")[0]
                        aci_class = get_aci_class(aci_class_identifier)
                        if not aci_class:
                            return False
                        data_dic = {}
                        data_dic['attributes'] = dict(dn=curr_node_dn)
                        cursor['children'][node] = {
                            'data': (aci_class, data_dic),
                            'name': node,
                            'children': {}
                        }
                cursor = cursor['children'][node]
            cursor['data'] = (nm, desc)
            cursor['name'] = path[-1]

    return tree, cmap


def parse_path(dn):
    """
    Grouping aware extraction of items in a path
    E.g. for /a[b/c/d]/b/c/d/e extracts [a[b/c/d/], b, c, d, e]
    """

    path = []
    buffer = ""
    i = 0
    while i < len(dn):
        if dn[i] == '[':
            while i < len(dn) and dn[i] != ']':
                buffer += dn[i]
                i += 1

        if dn[i] == '/':
            path.append(buffer)
            buffer = ""
        else:
            buffer += dn[i]

        i += 1

    path.append(buffer)
    return path


def get_aci_class(prefix):
    """
    Contains a hardcoded mapping between dn prefix and aci class.
    E.g for the input identifier prefix of "tn"
    this function will return "fvTenant"
    """

    if prefix == "tn":
        return "fvTenant"
    elif prefix == "epg":
        return "fvAEPg"
    elif prefix == "rscons":
        return "fvRsCons"
    elif prefix == "rsprov":
        return "fvRsProv"
    elif prefix == "rsdomAtt":
        return "fvRsDomAtt"
    elif prefix == "attenp":
        return "infraAttEntityP"
    elif prefix == "rsdomP":
        return "infraRsDomP"
    elif prefix == "ap":
        return "fvAp"
    elif prefix == "BD":
        return "fvBD"
    elif prefix == "subnet":
        return "fvSubnet"
    elif prefix == "rsBDToOut":
        return "fvRsBDToOut"
    elif prefix == "brc":
        return "vzBrCP"
    elif prefix == "subj":
        return "vzSubj"
    elif prefix == "rssubjFiltAtt":
        return "vzRsSubjFiltAtt"
    elif prefix == "flt":
        return "vzFilter"
    elif prefix == "e":
        return "vzEntry"
    elif prefix == "out":
        return "l3extOut"
    elif prefix == "instP":
        return "l3extInstP"
    elif prefix == "extsubnet":
        return "l3extSubnet"
    elif prefix == "rttag":
        return "l3extRouteTagPol"
    elif prefix == "rspathAtt":
        return "fvRsPathAtt"
    elif prefix == "leaves":
        return "infraLeafS"
    elif prefix == "taboo":
        return "vzTaboo"
    elif prefix == "destgrp":
        return "spanDestGrp"
    elif prefix == "srcgrp":
        return "spanSrcGrp"
    elif prefix == "spanlbl":
        return "spanSpanLbl"
    elif prefix == "ctx":
        return "fvCtx"
    else:
        return False


def find_tree_roots(tree):
    """
    Find roots for tree export. This involves finding all "fake" (dataless) nodes.
    E.g. for the tree
    __root__
        - a (no data)
            - b (data of /a/b)
            - c (no data)
                - d (data of /a/b/c/d)
                - e (data of /a/b/c/e)
            - f (data of /a/f)
        - z (data of /z)s
    This function will return [__root__, a, c]
    """
    if tree['data'] is not None:
        return [tree]

    roots = []
    for child in tree['children'].values():
        roots += find_tree_roots(child)

    return roots


def export_tree(tree):
    """
    Exports the constructed tree to a hierarchial json representation. (equal to tn-ansible, except for ordering)
    """
    tree_data = {
        'attributes': tree['data'][1]['attributes']
    }
    children = []
    for child in tree['children'].values():
        children.append(export_tree(child))

    if len(children) > 0:
        tree_data['children'] = children

    return {tree['data'][0]: tree_data}


def copy_children(tree, cmap):
    '''
    Copies existing children objects to the built tree
    '''
    for dn, children in cmap.items():
        aci_class = get_aci_class(
            (parse_path(dn)[-1]).split("-")[0])
        json_path_expr_search = parse('$..children.[*].{0}'.format(aci_class))
        json_path_expr_update = parse(str([str(match.full_path) for match in json_path_expr_search.find(
            tree) if match.value['attributes']['dn'] == dn][0]))
        curr_obj = [
            match.value for match in json_path_expr_update.find(tree)][0]
        if 'children' in curr_obj:
            for child in children:
                curr_obj['children'].append(child)
        elif 'children' not in curr_obj:
            curr_obj['children'] = []
            for child in children:
                curr_obj['children'].append(child)
        json_path_expr_update.update(curr_obj, tree)

    return


def create_structured_data(tree, cmap, output_file):
    if tree is False:
        logging.error(
            "Error parsing input file, unsupported object found in hierarchy.")
    tree_roots = find_tree_roots(tree)
    ansible_ds = {}
    for root in tree_roots:
        exp = export_tree(root)
        for key, val in exp.items():
            ansible_ds[key] = val
    copy_children(ansible_ds, cmap)
    toplevel = {"totalCount": "1", "imdata": []}
    toplevel['imdata'].append(ansible_ds)
    with open(output_file, 'w') as f:
        json.dump(toplevel, f)
    f.close()
