from bfx_hou.tools.importer.utils import import_ani_geometry
from bfx_hou.utils import node_operation
from bfx.api import create_burl
from collections import OrderedDict
from ast import literal_eval
from . import collect_shot_datas
from bfx.api import TaskContext
import json
import copy
import hou


__STEP_SUBNETWORK_NAMES__ = {'ani': 'Animation', 'cfx':'Character_FX', 'efx': 'FX',
                         'env': 'Environment', 'lay':'Layout', 'lgt':'Lighting',
                         'mmd':'Matchmove', 'sfn': 'Shot_Finalising'}
__TASK_CONTEXT__ = TaskContext.from_env()


class CollectDataFiles(object):

    """
    Hook class generate the extention data informations. If physically
    not version not exist it shows the gui of job id of kuidi

    :returns ext_datas -> extention_dict, extension_list,
                          related_assets, asset_instances
    """

    def datas(self):

        """
        Get necessary shot datas from the collect_shot_data module.
        Module return four datas belong to a shot. It do three task
            1.  Return a full pack of data information of a shot
            2.  Few cases for a shot asset instance and related assets
                wont be there. cases like animation was not published
                mmd and lay is published. mmd and lay doesnot have any
                assets only util datas. This case the related_assets
                and asset_instances return empty list. These case also
                shot builder allowed to build a scene the extention_dict
                it received.
            3.  If all returned ext_datas are empty then it trigger the gui
                and stop the shot builder to proceed further
                else it return entire datas
        """
        generate_data_dict = collect_shot_datas.GenerateExtensionDict()
        ext_datas = generate_data_dict.generate_ext_data()

        if 'sync_files' in ext_datas:
            data = ext_datas['sync_files']
            msg = 'Following Paths related the shot is not syncd\n'
            msg += 'Submitted In Kuaidi\n\n'
            for jobid, path in data.items():
                msg += '\n Job ID -> %s\t' % jobid
                msg += '  \n' + path
            hou.ui.displayMessage("{}".format(msg),
                                  title='Shot Builder')
            exit()
        elif not any(ext_datas):
            hou.ui.displayMessage("Scene version not exist or synced appropriately!\nPlease sync manually",
                                  title='Shot Builder')
            exit()
        elif not any(ext_datas[2:]):
            return ext_datas
        else:
            return ext_datas


class StoreDataFileStructures(CollectDataFiles):

    """
    First time shotbuilding call the CollectDataFiles hook class
    for generating all the necessary data-type infos. For the
    next consecutive time it take all datas from the node cache dict
    """

    def __init__(self):
        super(StoreDataFileStructures, self).__init__()

    def collect(self, node=None):

        if 'basset_dict' in node.userDataDict():
            get_ext_data = node.userDataDict()
            extention_dict = literal_eval(get_ext_data['basset_dict'])
            extension_list = literal_eval(get_ext_data['basset_list'])
            linked_assets = literal_eval(get_ext_data['linked_bassets'])
            asset_instance = literal_eval(get_ext_data['basset_instances'])
        else:
            get_ext_data = self.datas()
            extention_dict = get_ext_data[0]
            extension_list = get_ext_data[1]
            linked_assets = get_ext_data[2]
            asset_instance = get_ext_data[3]

        return extention_dict, extension_list, linked_assets, asset_instance


class BuildAllAssetInstanceNodes:

    """
    Class hook Create alembic sop and alembic archive
    basset nodes inside the respective step subnetwork.
    filename of alembic node setted with the
    founded extension dict path. if lod is passed
    the node name is created with basset and lod name.
    """

    def __init__(self,
                 step_sub_net_nodes,
                 step_or_basset_name,
                 ext_dict,
                 lod=None):
        """
        Loc node import mode is determined from the presets.
        If the mode is 1 for all the location files ani import
        HDA created and the founded path converted into a burl path
        and called with the main function

        :param step_sub_net_nodes: shotbuilder node
        :param step_or_basset_name: basset names
        :param ext_dict: nested dict
        :param lod: lod determined for only assets
                    None for util nodes like locator,
                    camera, static_geo,
        """
        generate_data_dict = collect_shot_datas.GenerateExtensionDict()
        self.loc_abc_import_mode = generate_data_dict.loc_abc_import_mode()
        self.step_sub_net_nodes = step_sub_net_nodes
        self.step_or_basset_name = step_or_basset_name
        self.ext_dict = ext_dict
        self.lod = lod

    def node_creation_switcher(self, camera_exist=False):

        """Method do a switch job. If camera exist True
        Then it create alembic archive. ele it create
        sopnode with alembic .

        :param camera_exist: False for non camera basset
                            True if camera basset found
        """

        if isinstance(self.ext_dict, dict):
            self.create_shot_asset_instance_nodes()
        else:
            self.create_util_nodes(camera_exist)

    def create_shot_asset_instance_nodes(self):

        """
        Create a subnet of basset if it is a asset and
        create a sop node with alembic node. If it is
        util node then only create a sop geo node with the
        alembic node inside it.
        """

        subnet_asset_node = self.step_sub_net_nodes.createNode('subnet')

        if not isinstance(self.lod, type(None)):
            subnet_name = self.step_or_basset_name+ '_' + self.lod
            subnet_asset_node.setName(subnet_name)
            subnet_asset_node.setUserData('name', subnet_name)
        else:
            subnet_asset_node.setName(self.step_or_basset_name)
            subnet_asset_node.setUserData('name', self.step_or_basset_name)

        for asset_atom_name, abc_path in self.ext_dict.items():
            abc_sop_node = subnet_asset_node.createNode('geo')
            abc_sop_node.setName(asset_atom_name)
            abc_sop_node.setUserData('name', asset_atom_name)
            abc_sop_node.setDisplayFlag(False)
            if not isinstance(self.lod, type(None)):
                abc_path_name = self.step_or_basset_name + '_' + self.lod
                basset_name = self.step_or_basset_name + '/' + self.lod + '/' + abc_sop_node.name()

                # If loc_abc_import_mode is 1 then ani import HDA imported
                # and the burl path sended to resolve
                if self.loc_abc_import_mode and asset_atom_name != 'model':
                    path = '/' + abc_path
                    ani_node = import_ani_geometry(create_burl(path), abc_sop_node)
                    ani_node.setName(abc_path_name)
                    ani_node.parm('mode').set(0)
                    ani_node.setUserData('name', abc_path_name)
                    ani_node.setUserData('parent_sub_network', step_sub_net_nodes.name())
                    ani_node.setUserData('subnet_basset_name', basset_name)
                    ani_node.setUserData('loc_abc_import_mode', str(self.loc_abc_import_mode))

                else:
                    abc_path_node = abc_sop_node.createNode('alembic')
                    abc_path_node.parm('fileName').set("/" + abc_path)
                    abc_path_node.parm('viewportlod').set(2)
                    abc_path_node.setName(abc_path_name)
                    abc_path_node.setUserData('name', abc_path_name)
                    abc_path_node.setUserData('parent_sub_network', step_sub_net_nodes.name())
                    abc_path_node.setUserData('subnet_basset_name', basset_name)
                    abc_path_node.setDisplayFlag(False)
            else:
                abc_path_node = abc_sop_node.createNode('alembic')
                abc_path_node.parm('viewportlod').set(2)
                abc_path_node.parm('fileName').set("/" + abc_path)
                abc_path_node.setName(self.step_or_basset_name)
                abc_path_node.setUserData('name', self.step_or_basset_name)
                abc_path_node.setUserData('parent_sub_network', step_sub_net_nodes.name())
                abc_path_node.setUserData('subnet_basset_name', self.step_or_basset_name)

                abc_path_node.setDisplayFlag(False)

    def create_util_nodes(self, camera_exist):

        """
        If camera found then alembic archieve created. Else it is util
        node as sop geo node created inside a alembic node on it.
        """

        if camera_exist:
            alembic_archive_node = self.step_sub_net_nodes.createNode('alembicarchive')
            alembic_archive_node.parm('viewportlod').set(2)
            alembic_archive_node.setName(self.step_or_basset_name)
            alembic_archive_node.setUserData('name', self.step_or_basset_name)
            alembic_archive_node.setUserData('camera', str(True))
            alembic_archive_node.setUserData('parent_sub_network',
                                                   self.step_sub_net_nodes.name()
                                                   )
            alembic_archive_node.parm('fileName').set("/" + self.ext_dict)
            alembic_archive_node.setDisplayFlag(False)
        else:
            asset_geo_nodes = self.step_sub_net_nodes.createNode('geo')
            asset_geo_nodes.setName(self.step_or_basset_name)
            asset_geo_nodes.setUserData('name', self.step_or_basset_name)
            asset_geo_nodes.setDisplayFlag(False)
            abc_path_node = asset_geo_nodes.createNode('alembic')
            abc_path_node.parm('viewportlod').set(2)
            if self.lod != None:
                temp_name = self.step_or_basset_name + '_' + self.lod
                basset_name = self.step_or_basset_name + '/' + self.lod + '/' + asset_geo_nodes.name()
                abc_path_node.setName(temp_name)
                abc_path_node.setUserData('name', temp_name)
                abc_path_node.setUserData('parent_sub_network',
                                                self.step_sub_net_nodes.name()
                                                )
                abc_path_node.setUserData('subnet_basset_name', basset_name)
            else:
                abc_path_node.setName(self.step_or_basset_name)
                abc_path_node.setUserData('name', self.step_or_basset_name)
                abc_path_node.setUserData('subnet_basset_name', self.step_or_basset_name)
                abc_path_node.setUserData('parent_sub_network',
                                                self.step_sub_net_nodes.name()
                                                )
            abc_path_node.parm('fileName').set("/" + self.ext_dict)
            abc_path_node.setDisplayFlag(False)


class BuildAssetInstanceMenu:

    """
    Class hook create menu instances of step subnetwork based upon the
    basset and asset found out. Number of instances created Based upon
    the specific step dict has. Menu has entries of founded asset name,
    asset version, lod, display, asset path and file path.

    Asset Name: Name of the basset. if util and camera it is just entered
                as it is. If lod found basset name is added with slash included
                joined text with asset type.
                Example: render_camera
                         stormBreaker_1/High/model
                         thorextreme_1/High/location
    Lod:        Lod menu setted up based upon the found lod of the respective asset
                if not fount it leave a default and might be hidded in later module
    Display:    Bounding box or Full geo display control
    Asset Path: Sets up the path of the final alembic node
    File Path:   Alembic path of the basset

    Asset menu instances only activated bassed upon the calculated step precedence
    rule. example sfn>ani>lay>mmd. if a basset found in both animation and layout
    step then both are loaded. the basset in layout is disabled cause animation
    took first precedence layout is second.

    Once a path is found it is added into
    a class variable to avoid duplication.

    """
    check_duplicates = []

    def __init__(self,
                 sub_net_node,
                 step_or_basset_name,
                 ext_dict,
                 precedence_rule,
                 lod=None):

        self.sub_net_node = sub_net_node
        self.ext_dict = ext_dict
        self.step_or_basset_name = step_or_basset_name
        self.precedence_rule = precedence_rule
        self.lod = lod

    def build_asset_instance_menu(self):

        """
        Create menu instances for all the found bassets. import toggle
        menu disable for the basset found in lowest precedence.

        Example: if thorextreme_1/High/location is found in sfn and also
        in ani. then thorextreme_1/High/location is menu entered in ani
        but the import option is disabled. cause sfn(sfn>ani>lay>mmd)
        took highest precedence compare to ani. if user chooses build
        shot at first time the thorextreme_1/High/location from sfn
        is created in sop context. Additionally, if 'model' and 'location'
        both exist for an asset then location is get priority. 'model'
        entry in the menu instance kept unchecked.

        All steps util and camera node import option is toggled based on
        above logic and created in obj context.
        """
        basset_mdl_loc_dict = {}
        loc_mdl_list = []
        lower_subnet_name = self.sub_net_node.userDataDict()['name'].lower()
        self.folder_template_name = "{}_assets".format(
                    lower_subnet_name
        )
        parm = self.sub_net_node.parm(self.folder_template_name)

        if isinstance(self.ext_dict, dict):
            for asset_atom_name, abc_path in self.ext_dict.items():
                if asset_atom_name not in loc_mdl_list:
                    loc_mdl_list.append(asset_atom_name)

                if 'model' in loc_mdl_list and 'location' in loc_mdl_list:
                    loc_mdl_list.remove('location') #Need to specify model here
                basset_mdl_loc_dict[self.step_or_basset_name] = loc_mdl_list
                path = abc_path

            if path not in self.check_duplicates:
                for _ in self.ext_dict.keys():
                    parm.insertMultiParmInstance(0)

                parm_index = 1

                for asset_atom_name, abc_path in self.ext_dict.items():

                    for step_name, asset_name_list in self.precedence_rule.items():
                        if __STEP_SUBNETWORK_NAMES__[step_name] == \
                                        self.sub_net_node.userDataDict()['name'] and \
                                        self.step_or_basset_name in asset_name_list and \
                                        asset_atom_name in basset_mdl_loc_dict[self.step_or_basset_name]:

                            self.sub_net_node.parm('%s_import_%s' %(
                                        lower_subnet_name,
                                        parm_index)
                            ).set(1)

                    basset_format = self.step_or_basset_name + "/" + self.lod + "/" + asset_atom_name

                    self.sub_net_node.parm('asset_name_%s' % parm_index).set(basset_format)

                    if 'High' in basset_format:
                        self.sub_net_node.parm('lod_%s' % parm_index).set(2)
                    elif 'Mid' in basset_format:
                        self.sub_net_node.parm('lod_%s' % parm_index).set(1)
                    elif 'Low' in basset_format:
                        self.sub_net_node.parm('lod_%s' % parm_index).set(0)

                    self.sub_net_node.parm('extension_path_%s' % parm_index).set("/"+abc_path)
                    self.check_duplicates.append(abc_path)
                    self.sub_net_node.parm('asset_path_%s' % parm_index).set("/obj/%s/%s/%s/%s" %(
                                                                        self.sub_net_node.parent().userDataDict()['otl_name'],
                                                                        self.sub_net_node.userDataDict()['name'],
                                                                        self.step_or_basset_name +'_'+self.lod,
                                                                        asset_atom_name)
                                                                        )
                    parm_index = parm_index + 1
            pass

        else:
            # All util nodes and camera basset entries for the menus setted true
            parm.insertMultiParmInstance(0)

            # if util geos exist in most priority step then the least priority
            # step having the same basset get disabled in the menu instance.
            # Example
            # If layout and mmd has both cameras. layout camera get visible
            # not mmd camera
            oparm_index = 1
            for step_name, asset_name_list in self.precedence_rule.items():
                if __STEP_SUBNETWORK_NAMES__[step_name] == \
                        self.sub_net_node.userDataDict()['name'] and \
                        self.step_or_basset_name in asset_name_list:
                    self.sub_net_node.parm('%s_import_%s' % (
                                    lower_subnet_name,
                                    oparm_index)
                    ).set(1)

                self.sub_net_node.parm('asset_name_%s' % oparm_index).set(self.step_or_basset_name)
                self.sub_net_node.parm('extension_path_%s' % oparm_index).set("/" + self.ext_dict)
                self.sub_net_node.parm('asset_path_%s' % oparm_index).set("/obj/%s/%s/%s" % (
                                                                        self.sub_net_node.parent().userDataDict()['otl_name'],
                                                                        self.sub_net_node.userDataDict()['name'],
                                                                        self.step_or_basset_name)
                                                                        )


class RemoveHigherLods:

    """
    Highest lods parameter in menu removed if same asset having multiple lods.
    The removable choice of group menu index is calculated from the passed lod_rule
    Responsible to Hide lod menus for util and camera menus.
    Only low lod group menu of the basset exist.
    If asset has 'low', 'mid', 'high' lods then 'mid' and 'high' lods menus
    groups get deleted.

    Example Lod Rule:
    -----------------

    {u'mmd': {}, u'lay': {'thorextreme_1': {'High': 2}, 'stormBreaker_1': {'High': 2}},
     u'ani': {'thorextreme_1': {'High': 2}, 'stormBreaker_1': {'High': 2}}}
    """

    def __init__(self,
                 shot_builder_node,
                 lod_rule,
                 deleted_sub_net,
                 asset_instancces):

        self.shot_builder_node = shot_builder_node
        self.lod_rule = lod_rule
        self.deleted_sub_net = deleted_sub_net
        self.asset_instances = asset_instancces
        self.parm_index_list = []
        self.parm_remove_index = {}

    def remove_high_lod(self):

        """
        If lod_create mode is false, it iterate through all the step subnet
        and get the asset name parameter instances. if lod of the
        asset specified in the lod_rule not matches with the same asset name
        with different lod, then that hole menu instance with the same index number
        removed

        Few cases, User toggled to other lod not in lod_rule and deleted a step subnetwork
        and it nodes in obj context. in case if he want to build the shot again by press
        shot builder 'Build Shot', based upon the lod_rule the unmatching toggled lod is
        group is deleted. To prevent situations these deleted_sub_net passed during recreation.
        The lod_rule is only applied to that recreating step subnetwork, not changes already
        existing subnetworks.

        Construct a parm_remove_index. Contains information of subnet work names as keys
        and list of index number of the subnetwork higher lods which menus need to be
        removed grouply.

        Example result of parm_remove_index
        -----------------------------------
        parm_remove_index = \
        {'Matchmove': [2, 3, 5], 'Animation': [4, 5, 6, 7, 10, 11], 'Layout': [2, 3, 5]}
        """

        if self.deleted_sub_net:
            delete_subnet = [__STEP_SUBNETWORK_NAMES__[name]
                              for name in self.deleted_sub_net]

        if not literal_eval(self.shot_builder_node.userDataDict()['lod_created']):
            for child_nodes in self.shot_builder_node.children():
                for step, basset_lods in self.lod_rule.items():
                    sub_net = __STEP_SUBNETWORK_NAMES__[step]

                    def remove_parm():
                        parm = child_nodes.parm(
                                    "{}_assets".format(
                                        child_nodes.userDataDict()['name'].lower()
                                    )
                        )

                        parm_index_set = set()
                        for parm_instances in parm.multiParmInstances():
                            if parm_instances.name().startswith('asset_name'):
                                for basset, lod in basset_lods.items():
                                    if basset in parm_instances.eval() \
                                                    and lod.keys()[0] not in parm_instances.eval():

                                        get_parm_index = int(
                                            parm_instances.name().split('_')[-1]
                                        ) - 1
                                        parm_index_set.add(get_parm_index)
                                        self.parm_remove_index[sub_net] = copy.deepcopy(list(parm_index_set))

                    # regenerating subnets some time
                    if self.deleted_sub_net:
                        if sub_net == child_nodes.userDataDict()['name'] and sub_net in delete_subnet:
                            remove_parm()
                    else:
                        if sub_net == child_nodes.userDataDict()['name']:
                            remove_parm()

            self.remove_higher_lod_parms()
            self.disable_utility_node_lod_menus()

    def disable_utility_node_lod_menus(self):

        """ Disable lod menus instance in util bassets"""

        for child_nodes in self.shot_builder_node.children():
            if child_nodes.userDataDict()['name'] == "Environment":
                continue
            parm = child_nodes.parm(
                "{}_assets".format(
                    child_nodes.userDataDict()['name'].lower()
                )
            )
            for parm_instances in parm.multiParmInstances():
                if parm_instances.name().startswith('asset_name'):
                    if parm_instances.eval().split('/')[0] not in self.asset_instances:
                        index = ''.join(name for name in parm_instances.name() if name.isdigit())
                        child_nodes.parm('lod_%s' %index).hide(True)

    def remove_higher_lod_parms(self):

        """
        Iterate through the parm_remove_index dict when matching subnet identified.
        If one menu instance removed then the following instance take that index as it
        current menu instance number. example if delete menu instance is 3
        menu instance 4 assigned to index 3. Deleteing menu instance based on the list numbers
        gonna remove un-necessary parameters.

        parm_remove_index =
        {'Matchmove': [2, 3, 5], 'Animation': [4, 5, 6, 7, 10, 11], 'Layout': [2, 3, 5]}
         [4, 5, 6, 7, 10, 11] list of index number which indicating which group of menu
         need annihilate.

        A increment counter is initiated when first index of the list of the subnetwork is removed
        Each time it decrement from the second list index number and so we get the rearranged menu instance
        number to remove.
        """

        for child_nodes in self.shot_builder_node.children():
            for step,parm_index in self.parm_remove_index.items():
                if child_nodes.userDataDict()['name'] == step:

                    parm = child_nodes.parm(
                        "{}_assets".format(
                            child_nodes.userDataDict()['name'].lower()
                        )
                    )
                    if len(parm_index) == 1:
                        for index in parm_index:
                                parm.removeMultiParmInstance(index)
                    else:
                        counter = 0
                        for index in parm_index:
                            if counter == 0:
                                parm.removeMultiParmInstance(index)
                            else:
                                parm.removeMultiParmInstance(index - counter)
                            counter = counter + 1
        pass


class BuildNodesSwitcher(StoreDataFileStructures):

    """Master Class resolve several logic and create step subnetworks
    and nodes in obj context based on the build mode

    A build mode determines whether to create all the master basset
    Network in the obj context or not. if true it build all the
    network connected to a master null node. Else it is a init shot
    pressed by user and only sub networks created by user no obj level
    context nodes. First time it call the inherited method to obtain the
    shot basset datas. All datas saved cached dictionary of the shot builder
    node. All next consecutive time data accessed from the user cache dictionary
    of shot builder not a data base call.

    Step and lod precedence dict obtained from the initial call.
    """

    def __init__(self, shot_builder_node, build_mode):

        """

        :param shot_builder_node: Current shot bulder HDA node
        :param build_mode: init shot or build shot mode determined.
                            True for build shot
        """

        super(BuildNodesSwitcher, self).__init__()

        self.abc_path_atom_keys = []
        self.camera_list = []
        self.store_created_asset_name = []
        self.shot_builder_node = shot_builder_node
        self.build_mode = build_mode
        self.get_ext_data = self.collect(node=shot_builder_node)
        self.extention_dict = self.get_ext_data[0]
        self.extension_list = self.get_ext_data[1]
        self.linked_assets = self.get_ext_data[2]
        self.asset_instances = self.get_ext_data[3]
        rule = StepPrecedence(self.extention_dict, self.linked_assets)
        self.precedence_rule = rule.make_precedence_dict()
        lod_rule = LodPrecedence(self.extention_dict, self.asset_instances)
        self.lod_rule = lod_rule.calc_precedence_dict()
        self.missing_nodes = []
        self.cache_datas()

    def build(self):

        """
        Inside shot builder is empty, then it call main method to build the
        step subnetwork and create nodes in obj context.

        Any nodes deleted by user and required recreation can be handled by exec().
        subnet nodes infos saved as asCode() recursively and missing node accessed from
        the shot builder cached data and do a build.
        """

        created_sub_nodes = set()
        for nodes in self.shot_builder_node.children():
            created_sub_nodes.add(nodes.userDataDict()['name'])

        if len(list(created_sub_nodes)) == 0:
            self.shot_builder_node.setUserData('lod_created', str(False))
            self.shot_builder_node.setUserData('deleted_sub_net', '[]')
            self.build_all_nodes()

        elif sorted(list(created_sub_nodes)) == \
                sorted(self.shot_builder_node.userDataDict()['created_steps']):
            if not self.build_mode:
                hou.ui.displayMessage("All Shot Steps Exist!!",
                                      title='Shot Builder')
                self.shot_builder_node.setUserData('lod_created', str(True))
                self.shot_builder_node.setUserData('deleted_sub_net', '[]')

        else:
            if 'cached_sub_nets' in self.shot_builder_node.userDataDict():

                self.shot_builder_node.setUserData('lod_created', str(False))
                sub_nodes_cache = {}
                for nodes in self.shot_builder_node.children():
                    index = __STEP_SUBNETWORK_NAMES__.values().index(nodes.userDataDict()['name'])
                    sub_nodes_cache[__STEP_SUBNETWORK_NAMES__.keys()[index]] = nodes.asCode(recurse=True)

                orig_sub_nets = set(self.extention_dict.keys())
                exist_sub_nets = set(sub_nodes_cache.keys())
                deleted_sub_nets = orig_sub_nets - exist_sub_nets
                self.shot_builder_node.setUserData('deleted_sub_net', str(list(deleted_sub_nets)))

                for nodes in list(deleted_sub_nets):
                    self.missing_nodes.append(__STEP_SUBNETWORK_NAMES__[nodes])
                    exec(literal_eval(self.shot_builder_node.userDataDict()['cached_sub_nets'])[nodes])
                self.cache_imp()

    def cache_imp(self):

        """Missing sub network node created and status updated to the user"""

        if self.missing_nodes:
            def node_cache_generator(missed_nodes):
                missed_nodes.setUserData(
                    'name',
                    missed_nodes.name()
                )
                for missed_node in missed_nodes.children():
                    node_cache_generator(missed_node)

            for missing_node in self.missing_nodes:
                hou_node = hou.node('/obj/%s/%s' %(
                            self.shot_builder_node,missing_node))
                node_cache_generator(hou_node)

            hou.ui.displayMessage('"{}" Missing Steps Created'.format(' , '.join(self.missing_nodes)),
                                  title='Shot Builder')

    def cache_datas(self):

        """
        Set node cache dict datas to re-access from the second time based upon the
        user request
        """

        if not self.shot_builder_node.userDataDict().has_key('basset_dict'):
            self.shot_builder_node.setUserData('basset_dict', str(self.extention_dict))
            self.shot_builder_node.setUserData('basset_list', str(self.extension_list))
            self.shot_builder_node.setUserData('linked_bassets', str(self.linked_assets))
            self.shot_builder_node.setUserData('otl_name', str(self.shot_builder_node.name()))
            self.shot_builder_node.setUserData('basset_instances', str(self.asset_instances))
            self.shot_builder_node.setUserData('lod_rule', str(self.lod_rule))

    def build_all_nodes(self):

        """
        A master hook which recursively resolve the nested generated dictionary
        create respective subnet, basset nodes with alembic nodes inside that.
        Menu instance creation called from the various part of the module to
        initiate all basset have a menu group entry.
        :return:
        """

        def call_menu_creation(step_sub_net_nodes,
                               step_or_basset_name,
                               ext_dict,
                               precedence_rule,
                               lod=None):

            """ Nested function to call instance menu creation class"""

            asset_menus = BuildAssetInstanceMenu(step_sub_net_nodes,
                                                        step_or_basset_name,
                                                        ext_dict,
                                                        precedence_rule,
                                                        lod=lod
                                                 )
            asset_menus.build_asset_instance_menu()

        def gen_nodes(ext_dict):

            """ Recursively solve ext_dict and create all basset related operations"""

            global step_sub_net_nodes, basset_names, camera_token

            if not isinstance(ext_dict, str):

                step_and_basset_names = ext_dict.keys()

                for step_or_basset_name in step_and_basset_names:
                    basset_names = step_or_basset_name

                    if step_or_basset_name in __STEP_SUBNETWORK_NAMES__.keys():

                        step_sub_net_nodes = self.shot_builder_node.createNode('subnet')
                        step_sub_net_nodes.setName(__STEP_SUBNETWORK_NAMES__[step_or_basset_name])
                        step_sub_net_nodes.setUserData('name',
                                                             __STEP_SUBNETWORK_NAMES__[step_or_basset_name])
                        sub_net_menu = CreateSubNetworkAssetMenus(step_sub_net_nodes)
                        sub_net_menu.create_sub_net_menus()

                    for linked_asset in self.linked_assets:
                        if linked_asset in step_or_basset_name:

                            for lods in ext_dict[step_or_basset_name].keys():
                                if 'High' == lods:
                                    lod = 'High'
                                if 'Mid' == lods:
                                    lod = 'Mid'
                                if 'Low' == lods:
                                    lod = 'Low'

                                self.abc_path_atom_keys.extend(ext_dict[step_or_basset_name][lod].keys())

                                if step_sub_net_nodes.children() == ():

                                    call_menu_creation(step_sub_net_nodes,
                                                       step_or_basset_name,
                                                       ext_dict[step_or_basset_name][lod],
                                                       self.precedence_rule,
                                                       lod)

                                    build_nodes = BuildAllAssetInstanceNodes(step_sub_net_nodes,
                                                                                 step_or_basset_name,
                                                                                 ext_dict[step_or_basset_name][lod],
                                                                                 lod)
                                    build_nodes.node_creation_switcher()

                                else:

                                    step_sub_net_nodes_node_names = [node.name()
                                                                     for node in step_sub_net_nodes.children()]

                                    basset_name_with_lod = step_or_basset_name + '_' + lod
                                    if basset_name_with_lod not in step_sub_net_nodes_node_names:

                                        call_menu_creation(step_sub_net_nodes,
                                                           step_or_basset_name,
                                                           ext_dict[step_or_basset_name][lod],
                                                           self.precedence_rule,
                                                           lod)

                                        build_nodes = BuildAllAssetInstanceNodes(step_sub_net_nodes,
                                                                                     step_or_basset_name,
                                                                                     ext_dict[step_or_basset_name][lod],
                                                                                     lod
                                                                                     )
                                        build_nodes.node_creation_switcher()

                    gen_nodes(ext_dict[step_or_basset_name])

            else:

                if basset_names not in list(set(self.abc_path_atom_keys)):
                    nodes = hou.node('/obj/%s/%s' % (
                                self.shot_builder_node.userDataDict()['otl_name'],
                                step_sub_net_nodes)
                    )
                    for basset_name_list in self.extension_list:
                        if basset_names in basset_name_list and 'camera' in basset_name_list:
                            self.camera_list.append(basset_names)
                            call_menu_creation(nodes,
                                               basset_names,
                                               ext_dict, self.precedence_rule)
                            build_nodes = BuildAllAssetInstanceNodes(nodes,
                                                                         basset_names,
                                                                         ext_dict)
                            build_nodes.node_creation_switcher(camera_exist=True)
                            break

                    if basset_names not in self.camera_list:

                        call_menu_creation(nodes,
                                           basset_names,
                                           ext_dict, self.precedence_rule)

                        build_nodes = BuildAllAssetInstanceNodes(nodes,
                                                                basset_names,
                                                                ext_dict)
                        build_nodes.node_creation_switcher()

        gen_nodes(self.extention_dict)

        def arrange_nodes(nodes):

            """ Inner function to arrange the nodes in all depth level"""

            children = nodes.children()

            def position_nodes(nodes):
                for node in nodes:
                    node.setPosition([node.position().x(), node.position().y() - 1])
                if nodes:
                    position_nodes(nodes[1:])

            position_nodes(list(children))
            for children_nodes in children:
                arrange_nodes(children_nodes)

        arrange_nodes(hou.node('/obj/%s' %self.shot_builder_node.userDataDict()['otl_name']))

        created_sub_nodes = {}
        sub_net_names = []
        for nodes in self.shot_builder_node.children():
            sub_net_names.append(nodes.userDataDict()['name'])
            index = __STEP_SUBNETWORK_NAMES__.values().index(nodes.userDataDict()['name'])
            created_sub_nodes[__STEP_SUBNETWORK_NAMES__.keys()[index]] = nodes.asCode(recurse=True)
            self.shot_builder_node.setUserData('cached_sub_nets', str(created_sub_nodes))
            self.shot_builder_node.setUserData('created_steps', str(sub_net_names))


def lock_all_instance_menus(shot_builder_node):

    """Independent hook to lock all menu instance"""

    for nodes in hou.node('/obj/%s' %shot_builder_node).children():
        if nodes.userDataDict()['name'] == "Environment":
            continue
        lowercase_subnet_name = nodes.userDataDict()['name'].lower()
        parm_instances_grp = nodes.parm('{}_assets'.format(lowercase_subnet_name))
        for parms in parm_instances_grp.multiParmInstances():
            if parms.name().startswith('asset_name') or \
                    parms.name().startswith('extension_path') or \
                    parms.name().startswith('asset_path'):
                parms.lock(True)
    pass


class CreateSubNetworkAssetMenus:

    """
    Class for creating subnetwork menus when solved by the build node switcher.
    A multi block list is created with all the required parameters.
    'Update' and 'Build selected Asset' button with call back scripts to
    create individual basset in the obj context
    """

    def __init__(self, subnet_node):

        self.subnet_node = subnet_node
        self.subnet_node_name = self.subnet_node.userDataDict()['name']

    def hide_existing_subnet_folders(self):

        """Hide all already existing parameters in newly created subnet"""

        parm_group = self.subnet_node.parmTemplateGroup()
        for parm_label in parm_group.entries():
            parm_group.hideFolder(parm_label.label(), True)
        self.subnet_node.setParmTemplateGroup(parm_group)

    def create_sub_net_menus(self):

        """Create list folder template parameters"""

        self.hide_existing_subnet_folders()
        parm_group = self.subnet_node.parmTemplateGroup()

        # Create Subnet menus for all the available assets
        folder_name = '{}_assets'.format(self.subnet_node_name.lower())
        folder_label = '{}_Assets'.format(self.subnet_node_name.title())
        shot_step_folders = hou.FolderParmTemplate(
            folder_name, folder_label,
            folder_type=hou.folderType.MultiparmBlock
        )

        toggle_name = '%s_import_#' %self.subnet_node_name.lower()
        asset_toggle = hou.ToggleParmTemplate(
            toggle_name,
            'Enable', join_with_next=True
        )
        asset_toggle.hideLabel(True)
        shot_step_folders.addParmTemplate(asset_toggle)

        asset_name_parm = hou.StringParmTemplate(
            "asset_name_#",
            "Asset Name", 1,
            disable_when="{%s ==0}" % toggle_name
        )
        shot_step_folders.addParmTemplate(asset_name_parm)

        asset_version_menu = hou.MenuParmTemplate(
            "asset_version_#",
            "Asset Version", (['1','2']),
            join_with_next=True,
            disable_when="{%s ==0}" % toggle_name
        )
        shot_step_folders.addParmTemplate(asset_version_menu)

        asset_lod_menu = hou.MenuParmTemplate(
            "lod_#",
            "LOD", (['Low', 'Mid', 'High']),
            join_with_next=True,
            disable_when="{%s ==0}" % toggle_name
        )
        shot_step_folders.addParmTemplate(asset_lod_menu)

        asset_display_menu = hou.MenuParmTemplate(
            "display_#",
            "Display", (['Bounding Box', 'Full Geometry']),
            disable_when="{%s ==0}" % toggle_name
        )
        shot_step_folders.addParmTemplate(asset_display_menu)

        asset_path_parm = hou.StringParmTemplate(
            "asset_path_#",
            "Asset Path", 1,
            disable_when="{%s ==0}" % toggle_name
        )
        shot_step_folders.addParmTemplate(asset_path_parm)

        extenstion_path_parm = hou.StringParmTemplate(
            "extension_path_#",
            "File Path", 1,
            disable_when="{%s ==0}" % toggle_name
        )
        shot_step_folders.addParmTemplate(extenstion_path_parm)

        spacer_parm = hou.SeparatorParmTemplate("space_#")
        shot_step_folders.addParmTemplate(spacer_parm)

        parm_group.append(shot_step_folders)

        update_button = hou.ButtonParmTemplate(
            "update", "Update",
            script_callback_language=hou.scriptLanguage.Python
        )
        update_button.setScriptCallback(
            "from bfx_hou.tools.shot_builder import build_user_selected_assets as busa;\
            reload(busa);up=busa.UpdateMenus(kwargs.get('node'));up.update_display()")
        parm_group.append(update_button)

        build_selected_asset_button = hou.ButtonParmTemplate(
            "build_selected_asset", "Build Selected Asset",
            script_callback_language=hou.scriptLanguage.Python
        )
        build_selected_asset_button.setScriptCallback(
                "from bfx_hou.tools.shot_builder import build_user_selected_assets as busa;\
                reload(busa);busa.BuildUserSelectedAssets(kwargs.get('node'))")
        parm_group.append(build_selected_asset_button)

        self.subnet_node.setParmTemplateGroup(parm_group)


class StepPrecedence:

    """
    Class for obtain step precedence dictionary
    Example search predence in efx builder preset
    ---------------------------------------------
    "step_precedence" : "sfn>ani>lay>mmd",

    This returns a dict which specify which menu groups
    need to disabled if same basset found in low precedence
    step subnetwork
    """

    def __init__(self,
                 extention_dict,
                 linked_assets):

        self.extention_dict = extention_dict
        self.linked_assets = linked_assets
        generate_data_dict = collect_shot_datas.GenerateExtensionDict()
        basset_rule_dict = generate_data_dict.presets
        if basset_rule_dict['step_precedence']:
            default_rule = basset_rule_dict['step_precedence']
        else:
            default_rule = 'sfn>ani>lay>mmd'
        self.precedence_rule = {}
        for index, step in enumerate(default_rule.split('>')):
            self.precedence_rule[step] = index
        self.precedence_dict = {}

    def make_precedence_dict(self):

        """
        Generate a dictionary with key of step names and values of basset occured
        for the step. The values are list
        """

        step_key_index = []
        step_key = self.extention_dict.keys()
        for key in step_key:
            if key in self.precedence_rule.keys():
                step_key_index.append(self.precedence_rule[key])

        min_index = min(step_key_index)
        key_of_min_index = self.precedence_rule.values().index(min_index)
        step_name = self.precedence_rule.keys()[key_of_min_index]

        global  high_precedence_stop_counter, \
                high_precedence_step, \
                combined_precedence_dict

        high_precedence_stop_counter = 0
        high_precedence_step = ''
        combined_precedence_dict = {}

        def _presedence_calc(extension_dict,
                             next_step_index,
                             step):

            global high_precedence_stop_counter, \
                    high_precedence_step

            if not type(extension_dict) == str:
                ext_keys = extension_dict.keys()
                # Few cases the next step for first incoming basset in just
                # A empty string. It leads to error. As so same step is assigned
                # as higher precedence
                for key in ext_keys:
                    if high_precedence_step == '':
                        high_precedence_step = step
                    combined_precedence_dict[key] = [step, high_precedence_step]
                    if high_precedence_stop_counter != 1:
                        high_precedence_stop_counter = 1
                        next_step_index = next_step_index + 1
                        next_index = self.precedence_rule.values().index(next_step_index)
                        next_step = self.precedence_rule.keys()[next_index]
                        high_precedence_step = next_step

                        if next_step in self.extention_dict.keys():
                            _presedence_calc(
                                self.extention_dict[next_step],
                                self.precedence_rule[next_step],
                                next_step
                            )

                    _presedence_calc(
                        extension_dict[key],
                        next_step_index,
                        step
                    )

        _presedence_calc(
            self.extention_dict[step_name],
            self.precedence_rule[step_name],
            step_name
        )

        self.precedence_dict = {}
        assets = []
        same_assets = []
        for key, value in combined_precedence_dict.items():
            if self.precedence_rule[value[0]] < self.precedence_rule[value[1]]:
                assets.append(key)
                self.precedence_dict[value[0]] = assets
            elif self.precedence_rule[value[0]] == self.precedence_rule[value[1]]:
                same_assets.append(key)
                self.precedence_dict[value[0]] = same_assets

        return self.precedence_dict


class LodPrecedence:

    """
    Class for obtain lod precedence. If basset belongs to the same step
    subnetwork has low, mid, high lod group menus then highest priority lod group menu
    instance is kept live. Other menu instances get removed. if mid, high is
    exist then high is removed. Low lod is always given priority one.

    Return the dict with all lod infos.
    Example:
    _______
    self.all_basset_lods = {
                            "mmd": {
                                "korg_1": {
                                    "High": 2,
                                    "Low": 0,
                                    "Mid": 1
                                },
                                "genericman_1": {
                                    "Low": 0
                                }
                            },
                            "lay": {
                                "korg_1": {
                                    "High": 2,
                                    "Low": 0,
                                    "Mid": 1
                                },
                                "genericman_1": {
                                    "Low": 0
                                }
                            },
                            "ani": {
                                "korg_1": {
                                    "High": 2,
                                    "Low": 0,
                                    "Mid": 1
                                },
                                "genericman_1": {
                                    "Low": 0
                                },
                                "korgclub_1": {
                                    "High": 2
                                }
                            }
                        }
    above example asset having more than one lod keys itereated and lowest priority
    keys are removed. 'Mid' and 'High' keys deleted in Korg_1. korgclub_1 has only 'High' it
    kept as it is as of it is already having only one lod
    """

    def __init__(self,
                 extension_dict,
                 asset_instances):

        self.extention_dict = extension_dict
        self.asset_instances = asset_instances
        self.steps = __STEP_SUBNETWORK_NAMES__.keys()
        self.default_lod_precedence = OrderedDict()
        self.default_lod_precedence['Low'] = 0
        self.default_lod_precedence['Mid'] = 1
        self.default_lod_precedence['High'] = 2
        self.low_precedence_key = min(self.default_lod_precedence.values())
        self.all_basset_lods = {}
        self.last_basset_occurance = []
        self.filter_list = []
        self.default_asset_lods = {}

    def calc_precedence_dict(self):

        def solve_precedence(ext_dict):

            basset_list = []
            lod_names = []
            lod_nos = []
            lod_with_no_dict = {}
            filter_dict_1 = {}
            filter_dict_2 = {}
            ext_dict_keys = ext_dict.keys()

            for keys in ext_dict_keys:
                if keys in self.steps:
                    global basset_key
                    basset_key = keys
                    self.all_basset_lods[basset_key] = {}
                    self.default_asset_lods[basset_key] = {}

                if keys in self.asset_instances:
                    self.default_asset_lods[basset_key][keys] = ext_dict[keys].keys()
                    lod_keys = self.default_lod_precedence.keys()
                    lod_with_no_dict1 = {}
                    for lod_name_list in self.default_asset_lods[basset_key][keys]:
                        if lod_name_list in lod_keys:
                            lod_with_no_dict1[lod_name_list] = self.default_lod_precedence[lod_name_list]
                            self.all_basset_lods[basset_key][keys] = copy.deepcopy(lod_with_no_dict1)

                    for lodname, _ in ext_dict[keys].items():
                        self.last_basset_occurance.append(keys)

                        if len(basset_list) <= 2:
                            for basset, lod_list in self.all_basset_lods[basset_key].items():
                                if basset != keys:
                                    lods = lod_list
                                    for cur_lod_names, _ in lods.items():
                                        if cur_lod_names == lodname:
                                            filter_dict_1[basset_key] = {}
                                            filter_dict_1[basset_key][basset] = cur_lod_names
                                            self.filter_list.append(filter_dict_1)
                        else:
                            for basset, lod_list in self.all_basset_lods[basset_key].items()[1:]:
                                if basset != keys:
                                    lods = lod_list
                                    for cur_lod_names, _ in lods.items():
                                        if cur_lod_names == lodname:
                                            filter_dict_2[basset_key] = {}
                                            filter_dict_2[basset_key][basset] = cur_lod_names
                                            self.filter_list.append(filter_dict_2)

                        if self.last_basset_occurance[self.last_basset_occurance.index(keys) - 1] != keys:
                            current_basset_list = []
                            current_lodnames = []
                            current_lodnos = []
                            current_lod_name_with_no_dict = {}
                            current_basset_list.append(keys)
                            current_lodnames.append(lodname)
                            current_lodnos.append(
                                self.default_lod_precedence[lodname]
                            )
                            current_lodnames = sorted(
                                        set(current_lodnames),
                                        key=current_lodnames.index
                            )
                            for lod_name, lod_no in zip(
                                    current_lodnames,
                                    list(OrderedDict.fromkeys(current_lodnos))
                            ):
                                current_lod_name_with_no_dict[lod_name] = lod_no
                            self.all_basset_lods[basset_key][current_basset_list[-1]] = \
                                        copy.deepcopy(current_lod_name_with_no_dict)
                if isinstance(ext_dict[keys], dict):
                    solve_precedence(ext_dict[keys])

        def remove_duplicates(basset_lods):

            remove_duplicate_filter = []
            if self.filter_list:
                for filters in self.filter_list:
                    if filters not in remove_duplicate_filter:
                        remove_duplicate_filter.append(filters)

            if remove_duplicate_filter:
                for filters_dict in remove_duplicate_filter:
                    for step, basset_with_lods in filters_dict.items():
                        for basset, lodname in basset_with_lods.items():

                            # The resulting basset lod list some cases contains only duplicate values
                            # ex basset_with_lods ={u'lay': {'thorextreme_1': {'High': 2},
                            #    'stormBreaker_1': {'High': 2}}, u'ani': {'thorextreme_1': {'High': 2},
                            #    'stormBreaker_1': {'High': 2}}}
                            #
                            # the duplicates are : {u'lay': {'thorextreme_1': 'High'}},
                            #                       {u'ani': {u'thorextreme_1': 'High'}
                            # the duplicate entry remove original values from the basset_with_lods
                            # Which results empty dict. as so we are counting if basset_with_lod
                            # Contains only one key then we wont remove it

                            if len(basset_lods[step][basset].keys()) > 1:
                                if basset in basset_lods[step] and lodname in basset_lods[step][basset]:
                                    basset_lods[step][basset].pop(lodname)
                                    return basset_lods

        def filter_lowest_precedence(solved_lod_predence_dict):

            lod_dict_keys = solved_lod_predence_dict.keys()

            for keys in lod_dict_keys:
                if keys in self.default_lod_precedence.keys():
                    min_lod = self.low_precedence_key

                    if self.default_lod_precedence.keys()[min_lod] in solved_lod_predence_dict:
                        temp_lod_keys = solved_lod_predence_dict.keys()
                        temp_lod_keys.remove(
                            self.default_lod_precedence.keys()[min_lod]
                        )
                        for lods in temp_lod_keys:
                            del solved_lod_predence_dict[lods]

                    next_lod = min_lod + 1
                    if self.default_lod_precedence.keys()[next_lod] in solved_lod_predence_dict:
                        next_temp_lod_keys = solved_lod_predence_dict.keys()
                        next_temp_lod_keys.remove(
                            self.default_lod_precedence.keys()[next_lod]
                        )
                        for lods in next_temp_lod_keys:
                            del solved_lod_predence_dict[lods]
                    break

                if isinstance(solved_lod_predence_dict[keys], dict):
                    filter_lowest_precedence(
                        solved_lod_predence_dict[keys]
                    )

        solve_precedence(self.extention_dict)
        res = remove_duplicates(self.all_basset_lods)
        if res:
            filter_lowest_precedence(res)
            return res
        else:
            filter_lowest_precedence(self.all_basset_lods)
            return self.all_basset_lods


class BuildMasterNetwork:

    """
    Consrturct nodes in obj context if build mode of BuildNodesSwitcher is True
    """

    def build(self, shot_builder_node):

        nodes = hou.node('/obj/%s' % shot_builder_node.userDataDict()['otl_name'])

        exsiting_sop_nodes = set()
        created_nodes = set()
        for sop_nodes in hou.node('/obj').children():
            if sop_nodes.userDataDict():
                if 'geo_node_name' in sop_nodes.userDataDict():
                    exsiting_sop_nodes.add(sop_nodes.userDataDict()['geo_node_name'])

        master_null_exist = 0
        for obj_cntxt_nodes in hou.node('/obj').children():
            if obj_cntxt_nodes.userDataDict():
                if 'MASTERNULL' in obj_cntxt_nodes.userDataDict() and \
                        obj_cntxt_nodes.userDataDict()['MASTERNULL'] == 'MASTERNULL':
                        master_null_exist = 1
                        master_null_node = obj_cntxt_nodes

        if not master_null_exist:
            master_null_node = hou.node("/obj").createNode('null')

            if 'MASTER_NULL' in [node.name() for node in hou.node('/obj').children()]:
                modifynodes = ModifyIdenticalNameNodes('MASTER_NULL')
                modifynodes.modify()

            master_null_node.setName('MASTER_NULL')
            master_null_node.setUserData('MASTERNULL', 'MASTERNULL')
            master_null_node.moveToGoodPosition()

        for sub_net_node in nodes.children():
            if sub_net_node.userDataDict()['name'] == "Environment":
                continue
            get_toggle_parm_name = sub_net_node.userDataDict()['name'].lower()
            folder_template_name = "{}_assets".format(get_toggle_parm_name)
            parm = sub_net_node.parm(folder_template_name)

            for parms in parm.multiParmInstances():
                if parms.name().startswith(get_toggle_parm_name):
                    if parms.eval():
                        index = parms.name().split('_')[-1]
                        geo_node_name = "{}_{}".format(
                                    get_toggle_parm_name,
                                    sub_net_node.parm('asset_name_%s' %index).eval().replace('/','_')
                        )
                        geo_asset_path = sub_net_node.parm('asset_path_%s' %index).eval()

                        if geo_asset_path.startswith('../'):
                            geo_asset_path = '/obj/%s' % \
                                                shot_builder_node.userDataDict()['otl_name'] + \
                                                '/' + \
                                                geo_asset_path.replace("../", '')

                        loc_abc_import_mode = 0
                        if hou.node(geo_asset_path).children():
                            alembic_node = hou.node(geo_asset_path).children()[0]
                            # Check the finally created node is alembic node or anim instance node
                            # If anim instance node detedcted then set animation mode to true
                            # as so it allow to create the sop node in obj context
                            if 'loc_abc_import_mode' in alembic_node.userDataDict():
                                loc_abc_import_mode = 1
                            node_type = hou.node(geo_asset_path).children()[0].type().name()

                        else:
                            file_path = sub_net_node.parm('extension_path_%s' %index).eval()
                            node_type = hou.node(geo_asset_path).type().name()

                        if node_type == 'alembic' or loc_abc_import_mode:

                            if geo_node_name not in list(exsiting_sop_nodes):

                                get_uncached_geo_node = DestroyNillCachedNodesConnected(master_null_node)
                                get_uncached_geo_node.destroy()

                                geo_nodes = hou.node("/obj").createNode('geo')
                                if geo_node_name in [node.name() for node in hou.node('/obj').children()]:
                                    modifynodes = ModifyIdenticalNameNodes(geo_node_name)
                                    modifynodes.modify()

                                geo_nodes.setName(geo_node_name)
                                geo_nodes.setUserData('geo_node_name', geo_node_name)
                                geo_nodes.setUserData('geo_asset_path', geo_asset_path)
                                geo_nodes.setPosition(
                                    hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).cursorPosition()
                                )
                                geo_nodes.setColor(hou.Color((0.71, 0.784, 1)))
                                object_merge_node = geo_nodes.createNode('object_merge')
                                object_merge_node.parm('xformtype').set(0)
                                object_merge_node.parm('objpath1').set(alembic_node.path())
                                object_merge_node_name = alembic_node.path().split('/')[-1]
                                object_merge_node.setName(object_merge_node_name)

                                unpack_node = geo_nodes.createNode('unpack')
                                unpack_node.setInput(0, object_merge_node)
                                unpack_node.bypass(True)
                                unpack_node.setPosition(
                                    [object_merge_node.position().x(),
                                     object_merge_node.position().y() - 3]
                                )

                                nullnode = geo_nodes.createNode('null')
                                nullnode.setInput(0, unpack_node)
                                nullnode.setPosition(
                                    [unpack_node.position().x(),
                                     unpack_node.position().y() - 3]
                                )
                                nullnode.setDisplayFlag(True)
                                nullnode.setRenderFlag(True)
                                nullnode_name = object_merge_node_name + '_OUT'
                                nullnode.setName(nullnode_name)
                                geo_nodes.setInput(0, master_null_node)
                                created_nodes.add(geo_nodes)

                        elif node_type == 'alembicarchive':

                            if geo_node_name not in list(exsiting_sop_nodes):

                                get_uncached_archieve_node = DestroyNillCachedNodesConnected(master_null_node)
                                get_uncached_archieve_node.destroy()

                                alembic_archive_node = node_operation.create_archive(file_path,
                                                                                     show= __TASK_CONTEXT__.show_name,
                                                                                     burl=create_burl(file_path),
                                                                                     toggled=1)

                                if geo_node_name in [node.name() for node in hou.node('/obj').children()]:
                                    modifynodes = ModifyIdenticalNameNodes(geo_node_name)
                                    modifynodes.modify()

                                alembic_archive_node.setName(geo_node_name)
                                alembic_archive_node.setUserData('geo_node_name', geo_node_name)
                                alembic_archive_node.setUserData('camera', str(True))
                                alembic_archive_node.setUserData('geo_asset_path', geo_asset_path)
                                alembic_archive_node.setPosition(
                                    hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor).cursorPosition()
                                )
                                alembic_archive_node.setColor(hou.Color((0.565, 0.494, 0.863)))
                                #alembic_archive_node.parm('fileName').set(file_path)
                                alembic_archive_node.setInput(0, master_null_node)
                                #alembic_archive_node.parm('buildHierarchy').pressButton()
                                created_nodes.add(alembic_archive_node)

        for sop_nodes in hou.node('/obj').children():
            if sop_nodes.userDataDict():
                if 'geo_node_name' in sop_nodes.userDataDict():
                    sop_nodes.setInput(0, master_null_node)

        if created_nodes:
            msg = 'Following Nodes Were Created inside /obj\n\n'
            for nodes in list(created_nodes):
                msg += nodes.name() + '\n'
            hou.ui.displayMessage("{}".format(msg),
                                  title='Shot Builder')

            created_nodes.add(master_null_node)
            hou.node("/obj").layoutChildren(
                items=[node for node in created_nodes],
                horizontal_spacing=0.5,
                vertical_spacing=0.5
            )
            shot_builder_node.setUserData('lod_created', str(True))

        else:
            hou.ui.displayMessage("All Shot Bassets Exist in /obj !!!""",
                                  title='Shot Builder')


class DestroyNillCachedNodesConnected:

    """Basset node with no cache user data is destroyed"""

    def __init__(self, root_node):

        self.root_node = root_node

    def destroy(self):
        if self.root_node.outputConnections():
            for null_node in self.root_node.outputConnections():
                if not null_node.outputNode().userDataDict():
                    null_node.outputNode().destroy()


class ModifyIdenticalNameNodes:

    """Basset node with no cache user data is renamed to duplicates"""

    def __init__(self, node_name):
        self.node_name = node_name

    def modify(self):
        node = hou.node("/obj/%s" %self.node_name)
        node.setName(self.node_name+'_bkp_1', unique_name=True)









