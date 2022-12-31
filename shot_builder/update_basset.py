#
# Process Module to make shotbuilder menu entry and basset node creation
# inside shotbuilder
#
from bfx_publisher.constant import CB_STATUS
from copy import deepcopy
from BQt import QtWidgets
from bfx_publisher.api import PublisherSectionWidget
from .build_init_shot import (__STEP_SUBNETWORK_NAMES__,
                               CreateSubNetworkAssetMenus)
import hou

__module_properties__ = {
    'label': 'Click publish to Update Basset in ShotBuilder',
    'description': "Load the basset into the Shot builder Context\n",
}

def process(logger,tool_context):

    """Receive Data From the section widget"""

    user_selected_basset_name_list = tool_context['new_extension_data'][0]
    user_selected_basset_list = tool_context['new_extension_data'][1]
    create_nodes_in_subnet_list = tool_context['new_extension_data'][2]
    new_extension_list = tool_context['new_extension_data'][3]
    new_asset_instances = tool_context['new_extension_data'][4]
    treewidget_items = tool_context['new_extension_data'][5]
    new_linked_assets = tool_context['new_extension_data'][6]

    logger.info("New Bassets Created with Menu entry\n%s" % '\n'.join(treewidget_items))

    class UpdateShotBuilder:

        """
        Create New nodes and respective menu entiries inside
        the shotbuilder HDA.
        """

        def __init__(self, *args):
            self.user_selected_basset_name_list = args[0]
            self.user_selected_basset_list = args[1]
            self.create_nodes_in_subnet_list = args[2]
            self.new_extension_list = args[3]
            self.new_asset_instances = args[4]
            self.new_linked_assets = args[5]
            self.basset_menu_list = []
            self.new_basset_lods_dict = {}
            self.new_basset_lods = []
            self.new_extension_list_from_user_selection = []
            self.shot_builder_node = UpdateShotBuilder.get_shot_builder_node()

        @staticmethod
        def get_shot_builder_node():
            for childen in hou.node('/obj').children():
                if 'otl_name' in childen.cachedUserDataDict():
                    return childen.cachedUserDataDict()['otl_name']

        def build_nodes_inside_subnet(self):

            """
            Contain several sub protoclols to do necessary steps
            to create subnet node and alembic nodes insde the
            shotbuilder HDA
            """

            def create_basset_network(subnetnode,
                                      new_basset_name,
                                      basset_lod,
                                      sopnodename,
                                      abcpath):

                high_lod_basset_subnetname = new_basset_name + '_' + basset_lod
                new_basset_subnet = subnetnode.createNode('subnet')
                new_basset_subnet.setName(high_lod_basset_subnetname)
                new_basset_subnet.setUserData('name', high_lod_basset_subnetname)
                sopnode = new_basset_subnet.createNode('geo')
                sopnode.setName(sopnodename)
                sopnode.setUserData('name', sopnodename)
                abc_path_node = sopnode.createNode('alembic')
                abc_path_node.parm('fileName').set("/" + abcpath)
                abc_path_node.parm('viewportlod').set(2)
                abc_path_node.setName(high_lod_basset_subnetname)

                subnet_basset_name = new_basset_name + '/' + basset_lod + '/' + sopnodename
                abc_path_node.setUserData('name', high_lod_basset_subnetname)
                abc_path_node.setUserData('parent_sub_network', subnetnode.name())
                abc_path_node.setUserData('subnet_basset_name', subnet_basset_name)
                abc_path_node.setDisplayFlag(False)

            def create_util_nodes(subnetnode,
                                  sopnodename,
                                  abcpath):

                new_util_node = subnetnode.createNode('geo')
                new_util_node.setName(sopnodename)
                new_util_node.setUserData('name', sopnodename)

                abc_path_node = new_util_node.createNode('alembic')
                abc_path_node.parm('fileName').set("/" + abcpath)
                abc_path_node.parm('viewportlod').set(2)
                abc_path_node.setName(sopnodename)
                abc_path_node.setUserData('name', sopnodename)
                abc_path_node.setUserData('parent_sub_network', subnetnode.name())
                abc_path_node.setUserData('subnet_basset_name', sopnodename)
                abc_path_node.setDisplayFlag(False)

            def create_alembic_archieve(subnetnode, abc_archieve_name, abc_cam_path):

                alembic_archive_node = subnetnode.createNode('alembicarchive')
                alembic_archive_node.parm('viewportlod').set(2)
                alembic_archive_node.setName(abc_archieve_name)
                alembic_archive_node.setUserData('name', abc_archieve_name)
                alembic_archive_node.setUserData('camera', str(True))
                alembic_archive_node.setUserData('parent_sub_network',
                                                       subnetnode.name()
                                                       )
                alembic_archive_node.parm('fileName').set("/" + abc_cam_path)
                alembic_archive_node.setDisplayFlag(False)

            def get_step_subnet_node(user_sel_dict):
                if isinstance(user_sel_dict, dict):
                    filtered_basset_keys = user_sel_dict.keys()

                    for filtered_basset_key in filtered_basset_keys:
                        if filtered_basset_key in __STEP_SUBNETWORK_NAMES__.keys():
                            subnet_name = __STEP_SUBNETWORK_NAMES__[filtered_basset_key]
                            shot_builder_node = hou.node('/obj/%s' %self.shot_builder_node)
                            for subnetchildren in shot_builder_node.children():
                                if subnetchildren.cachedUserDataDict()['name'] == subnet_name:
                                    return subnetchildren
                                else:
                                    step_subnet = shot_builder_node.createNode('subnet')
                                    step_subnet.setName(subnet_name)
                                    step_subnet.setCachedUserData('name', subnet_name)
                                    sub_net_menu = CreateSubNetworkAssetMenus(step_subnet)
                                    sub_net_menu.create_sub_net_menus()
                                    logger.info("New Step SubnetWork Created\n\n%s" %step_subnet.name())
                                    return step_subnet

            def build_nodes(basset_dict):

                """
                An master function which recursively solve the incoming dict structure
                and determines which nodes need to be created based upon the passing
                information. if it is asset then it is create subnet inside it create
                alembic nodes else it resposible to create util sop nodes with the
                alembic node.
                """

                if not isinstance(basset_dict, str):
                    if basset_dict.keys()[0] in __STEP_SUBNETWORK_NAMES__.keys():
                        global buildnode_dubnet
                        buildnode_dubnet = get_step_subnet_node(basset_dict)

                subnet_step_full_names = __STEP_SUBNETWORK_NAMES__.values()
                index_subnet_step = subnet_step_full_names.index(
                            buildnode_dubnet.cachedUserDataDict()['name']
                )
                subnet_step_name = __STEP_SUBNETWORK_NAMES__.keys()[index_subnet_step]

                if isinstance(basset_dict, dict):
                    new_basset_keys = basset_dict.keys()

                    for new_basset_key in new_basset_keys:
                        if new_basset_key in self.new_asset_instances:
                            new_basset_name = new_basset_key

                            for lods in ['High', 'Mid', 'Low']:
                                if lods in basset_dict[new_basset_name]:
                                    for sopnodename, abcpath in basset_dict[new_basset_name][lods].items():

                                        create_basset_network(buildnode_dubnet,
                                                              new_basset_name,
                                                              lods,
                                                              sopnodename,
                                                              abcpath)
                                        abcpath = '/' + abcpath
                                        for new_ext_list in self.new_extension_list:
                                            if subnet_step_name in new_ext_list and \
                                                    new_basset_name in new_ext_list and \
                                                    lods in new_ext_list and \
                                                    sopnodename in new_ext_list and \
                                                    abcpath in new_ext_list:
                                                self.new_extension_list_from_user_selection.append(new_ext_list)


                            break
                        else:
                            if new_basset_key == 'camera':
                                for name, _ in basset_dict[new_basset_key].items():
                                    for abc_archieve_name, abc_cam_path in basset_dict[new_basset_key][name].items():

                                        create_alembic_archieve(buildnode_dubnet,
                                                                abc_archieve_name,
                                                                abc_cam_path)

                                        abc_cam_path = '/' + abc_cam_path
                                        for new_ext_list in self.new_extension_list:
                                            if subnet_step_name in new_ext_list and \
                                                    new_basset_key in new_ext_list and \
                                                    abc_archieve_name in new_ext_list and \
                                                    abc_cam_path in new_ext_list:
                                                self.new_extension_list_from_user_selection.append(new_ext_list)
                                        pass
                                break
                            else:
                                if isinstance(basset_dict[new_basset_key], str):
                                    for sopnodename, abcpath in basset_dict.items():
                                        create_util_nodes(buildnode_dubnet,
                                                          sopnodename,
                                                          abcpath)

                                        abcpath = '/' + abcpath
                                        for new_ext_list in self.new_extension_list:
                                            if subnet_step_name in new_ext_list and \
                                                    sopnodename in new_ext_list and \
                                                    abcpath in new_ext_list:
                                                self.new_extension_list_from_user_selection.append(new_ext_list)
                                        pass
                        build_nodes(basset_dict[new_basset_key])

            def build_instance_menu(filtered_user_dict):

                """
                Create a new entry in the respective step subnetwork and rigister
                entiries based upon the basset choosed by the user
                """
                def menu_instance_entry(userseldict):
                    if isinstance(userseldict, dict):
                        filtered_basset_keys = userseldict.keys()
                        global cur_subnetnode
                        for basset_keys in filtered_basset_keys:
                            if basset_keys in __STEP_SUBNETWORK_NAMES__.keys():
                                cur_subnetnode = __STEP_SUBNETWORK_NAMES__[basset_keys]
                            if basset_keys in self.new_asset_instances:
                                global asset_name
                                asset_name = basset_keys
                                lod_keys = userseldict[basset_keys].keys()[0]
                                tmp_basset_type = userseldict[basset_keys][lod_keys]

                                basset_name = asset_name + '/' + lod_keys + '/' + tmp_basset_type.keys()[0]
                                node_name = asset_name + '_' + lod_keys
                                asset_path = "/obj/%s/%s/%s/%s" % (self.shot_builder_node,
                                                                   cur_subnetnode,
                                                                   node_name,
                                                                   tmp_basset_type.keys()[0])
                                file_path = tmp_basset_type.values()[0]
                                tmp_basset_dict = {'asset_name': basset_name, 'asset_path': asset_path,
                                                   'file_path': file_path, 'cur_subnetnode': cur_subnetnode,
                                                   'lod': lod_keys, 'lod_menu': True}
                                self.basset_menu_list.append(tmp_basset_dict)
                                break
                            else:
                                for val in userseldict.values():
                                    if isinstance(val, str):
                                        basset_name = userseldict.keys()[0]
                                        asset_path = "/obj/%s/%s/%s" %(self.shot_builder_node,
                                                                       cur_subnetnode,
                                                                       basset_name)
                                        file_path = userseldict.values()[0]
                                        tmp_basset_dict = {'asset_name': basset_name, 'asset_path': asset_path,
                                                           'file_path': file_path, 'cur_subnetnode': cur_subnetnode,
                                                           'lod_menu': False}
                                        self.basset_menu_list.append(tmp_basset_dict)

                            menu_instance_entry(userseldict[basset_keys])

                for userseldict in filtered_user_dict:
                    menu_instance_entry(userseldict)
                    pass

                for menu_entities in self.basset_menu_list:
                    hou_cur_sub_net_node = hou.node("/obj/%s/%s" %(self.shot_builder_node,
                                                                   menu_entities['cur_subnetnode']))
                    lower_subnet_name = hou_cur_sub_net_node.cachedUserDataDict()['name'].lower()
                    folder_template_name = "{}_assets".format(
                        lower_subnet_name
                    )
                    parm_instances = hou_cur_sub_net_node.parm(folder_template_name)
                    parm_count_start = parm_instances.eval()
                    parm_instances.insertMultiParmInstance(parm_count_start)

                    parm_index = parm_count_start + 1

                    hou_cur_sub_net_node.parm('%s_import_%s' %(lower_subnet_name, parm_index)).set(1)
                    hou_cur_sub_net_node.parm('asset_name_%s' %(parm_index)).set(menu_entities['asset_name'])
                    hou_cur_sub_net_node.parm('asset_name_%s' % (parm_index)).lock(1)
                    hou_cur_sub_net_node.parm('asset_path_%s' %(parm_index)).set(menu_entities['asset_path'])
                    hou_cur_sub_net_node.parm('asset_path_%s' % (parm_index)).lock(1)
                    filepath = '/' + menu_entities['file_path']
                    hou_cur_sub_net_node.parm('extension_path_%s' % (parm_index)).set(filepath)
                    hou_cur_sub_net_node.parm('extension_path_%s' % (parm_index)).lock(1)
                    if 'lod' in menu_entities:
                        subnet_step_full_names = __STEP_SUBNETWORK_NAMES__.values()
                        index_subnet_step = subnet_step_full_names.index(menu_entities['cur_subnetnode'])
                        subnet_step_names = __STEP_SUBNETWORK_NAMES__.keys()[index_subnet_step]
                        if menu_entities['lod'] == 'Low':
                            hou_cur_sub_net_node.parm('lod_%s' %parm_index).set(0)
                            self.new_basset_lods_dict[subnet_step_names] = {asset_name: {'Low': 0}}
                            self.new_basset_lods.append(self.new_basset_lods_dict)
                        elif menu_entities['lod'] == 'Mid':
                            hou_cur_sub_net_node.parm('lod_%s' %parm_index).set(1)
                            self.new_basset_lods_dict[subnet_step_names] = {asset_name: {'Mid': 1}}
                            self.new_basset_lods.append(self.new_basset_lods_dict)
                        elif menu_entities['lod'] == 'High':
                            hou_cur_sub_net_node.parm('lod_%s' %parm_index).set(2)
                            self.new_basset_lods_dict[subnet_step_names] = {asset_name: {'High': 2}}
                            self.new_basset_lods.append(self.new_basset_lods_dict)

                    if not menu_entities['lod_menu']:
                        hou_cur_sub_net_node.parm('lod_%s' % (parm_index)).hide(1)

            for new_basset_dict in self.create_nodes_in_subnet_list:
                build_nodes(new_basset_dict)
                pass

            build_instance_menu(self.user_selected_basset_list)

        def update_node_metadatas(self):

            """
            All user selected filtered basset information updated into the respective
            Shotbuilder cachedUserDataDict.
            """

            shot_builder_node = hou.node('/obj/%s' % self.shot_builder_node)
            basset_instances = deepcopy(shot_builder_node.cachedUserDataDict()['basset_instances'])
            get_lod_rule = deepcopy(shot_builder_node.cachedUserDataDict()['lod_rule'])
            get_basset_dict = deepcopy(shot_builder_node.cachedUserDataDict()['basset_dict'])
            get_basset_list = deepcopy(shot_builder_node.cachedUserDataDict()['basset_list'])

            def merge_new_dict_with_orig(orig_dict, new_dict):
                for key in new_dict:
                    if key in orig_dict and isinstance(orig_dict[key], dict) and isinstance(new_dict[key], dict):
                        merge_new_dict_with_orig(orig_dict[key], new_dict[key])
                    else:
                        orig_dict[key] = new_dict[key]

            for created_nodes in self.create_nodes_in_subnet_list:
                merge_new_dict_with_orig(get_basset_dict, created_nodes)

            for created_new_lod_rule in self.new_basset_lods:
                merge_new_dict_with_orig(get_lod_rule, created_new_lod_rule)

            def update_basset_dict():
                shot_builder_node.setUserData('basset_dict', str(get_basset_dict))

            def update_lod_rule():
                shot_builder_node.setUserData('lod_rule', str(get_lod_rule))

            def update_basset_instance():
                basset_instances.append(asset_name)
                shot_builder_node.setUserData('basset_instances', str(basset_instances))

            def update_linked_basset():
                shot_builder_node.setUserData('linked_bassets', str(self.new_linked_assets))

            def update_extension_list():
                for usr_selected_items in self.new_extension_list_from_user_selection:
                    get_basset_list.append(usr_selected_items)
                shot_builder_node.setUserData('basset_list', str(get_basset_list))

            update_basset_dict()
            update_lod_rule()
            update_basset_instance()
            update_linked_basset()
            update_extension_list()

    obj = UpdateShotBuilder(user_selected_basset_name_list,
                            user_selected_basset_list,
                            create_nodes_in_subnet_list,
                            new_extension_list,
                            new_asset_instances,
                            new_linked_assets)
    obj.build_nodes_inside_subnet()
    obj.update_node_metadatas()
    return CB_STATUS.OK