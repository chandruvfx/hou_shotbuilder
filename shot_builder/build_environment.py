from bfx.data.prod.shotgun.production2.models import (Show,
                                                      Asset,
                                                      Shot)
from bfx.api import (TaskContext,
                     PLE_Version,
                     PLE_Entity)
from bfx_hou.tools.importer.core.locationatom import LocationOperation
from ast import literal_eval
import json
import hou


class BuildEnvironment:

    """
    Build environment if shotgun entry of related asset set found.
    Build mode specify it is build obj context level node or just
    'Init Shot' with partially loaded subnetwork.

    Example
    _______

    build_env = build_environment.BuildEnvironment(shot_builder_node, build_mode=True)
    build_env.build()
    """

    def __init__(self, shot_builder_node, build_mode, loc_json=None):

        """

        :param shot_builder_node: current shot builder node
        :param build_mode: build mode to build shot or init shot
        :param loc_json: resolved location json file
        """
        self.shot_builder_node = shot_builder_node
        self.build_mode = build_mode
        self.env_creation_mode = False
        self.loc_json = loc_json
        self.env_data = {}

    def locate_json(self):

        """
        Obtain location.json using SG query. 'lay' step only has set information
        :return: location.json file
        """
        if self.loc_json:
            return self.loc_json

        else:
            task_cntx = TaskContext.from_env()
            sg_show = Show.get(name=task_cntx.show_name)
            sg_asset_instances = Shot.select().where(
                            (Shot.show == sg_show) &
                            (Shot.name == task_cntx.shot_name)
            ).get()
            sg_asset_list = [assets.name
                             for assets in sg_asset_instances.assets
                             ]
            show_name = task_cntx.show_name
            set_name = ''
            for assets in sg_asset_list:
                if sg_show.assets.select().where(Asset.name == assets).get().type == 'Set':
                    set_name = sg_show.assets.select().where(Asset.name == assets).get().name

            if len(set_name) == 0:
                self.env_creation_mode = False
                return self.env_creation_mode

            else:
                basset_set = "{}/{}/{}".format(show_name, set_name, 'lay')
                ent = PLE_Entity.find(basset_set)
                basset = ent.find_asset(asset_name=set_name)
                version = basset.get_latest_version()
                atom_object = version.get_exporter().get_atom_object()

                return atom_object.get_part('location')

    def create_env_sub_net(self):

        """
        Create Environment subnetwork inside the shot builder node
        Create user cache dict for the subnet
        """

        self.sub_net_node = self.shot_builder_node.createNode('subnet')
        self.sub_net_node.setName('Environment')
        self.sub_net_node.setUserData('name', 'Environment')
        created_steps = literal_eval(self.shot_builder_node.userDataDict()['created_steps'])
        if self.sub_net_node.userDataDict()['name'] not in created_steps:
            created_steps.append(self.sub_net_node.userDataDict()['name'])
            self.shot_builder_node.setUserData('created_steps', str(created_steps))

    def create_menus(self):

        """
        Create main menu for Env subnet
        """

        # Delete all the exsiting parms
        del_grp = self.sub_net_node.parmTemplateGroup()
        for parm_label in del_grp.entries():
            del_grp.hideFolder(parm_label.label(), True)
        self.sub_net_node.setParmTemplateGroup(del_grp)

        parm_group = self.sub_net_node.parmTemplateGroup()

        location_folder = hou.FolderParmTemplate(
            "locations_files", "Locations",
            folder_type=hou.folderType.MultiparmBlock
        )
        space_location_folder_grp = hou.FolderParmTemplate(
            "location_group_#", "\"\"",
            folder_type=hou.folderType.Simple
        )

        location_path_parm = hou.StringParmTemplate(
            "location_path_#",
            "Location File", 1, join_with_next=True,
        )
        space_location_folder_grp.addParmTemplate(location_path_parm)

        location_create_option_parm = hou.MenuParmTemplate(
                    "location_option_#",
                    "Create Options",
                    (['Use Alembic Archive', 'Use Instance', 'Use Copy']),
                    join_with_next=True,
                    disable_when="{location_abc_list_# == 0 }"
        )
        location_create_option_parm.hideLabel(True)
        space_location_folder_grp.addParmTemplate(location_create_option_parm)

        location_build_scene_button_parm = hou.ButtonParmTemplate(
                        "location_build_scene_#", "Build Scene",
                        disable_when="{location_abc_list_# == 0 }",
                        script_callback_language=hou.scriptLanguage.Python
        )
        location_build_scene_button_parm.setScriptCallback(
            "from bfx_hou.tools.basset_node import load_files;reload(load_files);load_files.location_function(kwargs)"
        )
        space_location_folder_grp.addParmTemplate(location_build_scene_button_parm)

        location_detail_folder = hou.FolderParmTemplate(
            "location_detail_#", "Environment Bassets Details",
            folder_type=hou.folderType.Collapsible
        )

        location_load_all_toggle = hou.ToggleParmTemplate(
            'load_all_#',
            'Load All',
            join_with_next=True,
            disable_when="{location_abc_list_# == 0 }",
            script_callback_language=hou.scriptLanguage.Python
        )
        location_load_all_toggle.setScriptCallback(
            "from bfx_hou.tools.basset_node import load_files;reload(load_files);load_files.load_all(kwargs)"
        )
        location_detail_folder.addParmTemplate(location_load_all_toggle)

        location_abc_list_folder = hou.FolderParmTemplate(
            "location_abc_list_#", "Files",
            folder_type=hou.folderType.ScrollingMultiparmBlock
        )

        location_file_folder_grp = hou.FolderParmTemplate(
            "location_file_group_#_#", "\"\"",
            folder_type=hou.folderType.Simple
        )

        location_load_toggle = hou.ToggleParmTemplate(
            'is_load_#_#',
            'Load', join_with_next=True
        )
        location_file_folder_grp.addParmTemplate(location_load_toggle)

        location_name_parm = hou.StringParmTemplate(
            "location_name_#_#",
            "Name", 1, join_with_next=True
        )
        location_file_folder_grp.addParmTemplate(location_name_parm)

        location_type_parm = hou.StringParmTemplate(
            "location_type_#_#",
            "Type", 1, join_with_next=True
        )
        location_file_folder_grp.addParmTemplate(location_type_parm)

        location_node_parm = hou.StringParmTemplate(
            "location_node_#_#",
            "Node", 1
        )
        location_file_folder_grp.addParmTemplate(location_node_parm)

        location_path_parm = hou.StringParmTemplate(
            "location_path_#_#",
            "Path", 1,
        )
        location_file_folder_grp.addParmTemplate(location_path_parm)

        location_abc_list_folder.addParmTemplate(location_file_folder_grp)
        location_detail_folder.addParmTemplate(location_abc_list_folder)
        space_location_folder_grp.addParmTemplate(location_detail_folder)

        location_folder.addParmTemplate(space_location_folder_grp)
        parm_group.append(location_folder)
        self.sub_net_node.setParmTemplateGroup(parm_group)

    @staticmethod
    def delete_existing_env_nodes():

        """ Destroy all env node in obj context
        if env node has specific dict key"""

        for nodes in hou.node('/obj').children():
            if nodes.userDataDict():
                if 'env_geo_node_name' in nodes.userDataDict():
                    if nodes.parentNetworkBox():
                        nodes.parentNetworkBox().destroy()
                    nodes.destroy()

    def create_menu_instances(self):

        """
        Create main menu instance for Env subnet based upon the loction
        json parsed

        Enter location json in main file tab and Call the LocationOperation
        to build the network if build mode is true
        """

        if self.build_mode:
            BuildEnvironment.delete_existing_env_nodes()

        location_file = self.locate_json()
        if location_file.endswith('json'):

            location_parm = self.sub_net_node.parm('locations_files')
            location_parm.insertMultiParmInstance(0)

            location_path_parm = self.sub_net_node.parm('location_path_1')
            location_path_parm.set(location_file)

            location_option_parm = self.sub_net_node.parm('location_option_1')
            location_option_parm.set(1)

            group_index = 1
            lo = LocationOperation(location_file, self.sub_net_node , 1)
            lo.load_json_info(group_index)
            self.sub_net_node.setUserData('load_json_info', str(lo))
            if self.build_mode:
                lo.build_scene(group_index)
                self.connect_env_to_master_null()
    pass

    def connect_env_to_master_null(self, subnet_node=None):

        """
        Connect env nodes in object context to master null node
        if exist else create master null then connect it
        """
        if subnet_node:
            self.sub_net_node = subnet_node

        env_asset_name_list = set()
        env_asset_nodes = set()
        abc_ist = self.sub_net_node.parm('location_abc_list_1')
        for parms in abc_ist.multiParmInstances():
            if parms.name().startswith('location_name'):
                env_asset_name_list.add(parms.eval().split('/')[-1])

        for nodes in hou.node('/obj').children():
            for env_asset_name in env_asset_name_list:
                if env_asset_name in nodes.name():
                    env_asset_nodes.add(nodes)
                    nodes.setUserData('env_geo_node_name', nodes.name())

        master_nullnode = self.__create_master_null()
        for env_nodes in env_asset_nodes:
            env_nodes.setInput(0, master_nullnode)
        pass
        if env_asset_nodes:
            hou.node("/obj").layoutChildren(
                items=[envnode for envnode in env_asset_nodes],
                horizontal_spacing=2,
                vertical_spacing=1
            )

    def __create_master_null(self):

        """ Create master null if not exist"""

        master_null_exist = 0
        for nodes in hou.node('/obj').children():
            if nodes.userDataDict():
                if 'MASTERNULL' in nodes.userDataDict() and \
                        nodes.userDataDict()['MASTERNULL'] == 'MASTERNULL':
                    master_null_exist = 1
                    self.master_nullnode = nodes

        if not master_null_exist:
            self.master_nullnode = hou.node("/obj").createNode('null')
            self.master_nullnode.setName('MASTER_NULL')
            self.master_nullnode.setUserData('MASTERNULL', 'MASTERNULL')

        return self.master_nullnode

    def build(self):

        """Master method call to build set env

        If location json file exist then it proceed further.
        If version changed from version tracker then it destroy the entire
        environment set network and recreate it based upon the user selected version.
        """

        location_file = self.locate_json()
        if location_file:

            envnode = []
            for nodes in self.shot_builder_node.children():
                if nodes.userDataDict():
                    if nodes.userDataDict()['name'] == 'Environment':
                        envnode.append(nodes.userDataDict()['name'])

            if not envnode:
                self.create_env_sub_net()
                self.create_menus()
                self.create_menu_instances()
            else:
                if self.build_mode:
                    print("Destroying exisiting environment.Creating New")
                    BuildEnvironment.delete_existing_env_nodes()
                    env_sub_net = hou.node("/obj/%s/%s" % (
                                self.shot_builder_node.userDataDict()['otl_name'],
                                envnode[0]
                    ))
                    env_sub_net.parm('location_build_scene_1').pressButton()
                    self.connect_env_to_master_null(subnet_node=env_sub_net)


    




