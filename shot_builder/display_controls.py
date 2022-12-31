from collections import OrderedDict
from .build_init_shot import __STEP_SUBNETWORK_NAMES__
from copy import deepcopy
import hou


class LOD:

    """
    Shot builder node callback script to change the lods inside step subnetwork.
    Changing lods for a specific subnet gonna change entire lod for all the basset
    entries if the specific lod exist for the basset. If requested lod is exist it
    changes else it leaves unchanged


    Example:
    --------
        disp_ctrl = display_controls.LOD(
                            shot_builder_node,
                            shot_builder_node.userDataDict()['basset_instances'])
        disp_ctrl.change_lods()
    """
    def __init__(self,
                 shot_builder_node,
                 asset_instances
                 ):

        self.shot_builder_node = shot_builder_node
        self.lod_dict = OrderedDict()
        self.asset_instances = asset_instances
        self.changed_lod_info = {}
        self.default_lods = {0: 'Low', 1: 'Mid', 2: 'High'}
        self.high_lod_last_temp = ''
        self.low_lod_last_temp = ''
        self.mid_lod_last_temp = ''

    def make_lod_dict(self):

        """
        Create lod dict from the parm list menu created

        Example:
        -------
        OrderedDict([('group1', 'Matchmove'), ('lod1', 'Low'), ('display1', 'Full Geometry'),
        ('group2', 'Animation'), ('lod2', 'Mid'), ('display2', 'Bounding Box')])
        """

        lod_parm = self.shot_builder_node.parm('lod_display')
        temp_lods = []
        temp_parm_names = []

        for parms in lod_parm.multiParmInstances():

            index = parms.eval()
            parm_index = parms.name().split("_")[-1]
            key_names = ''.join(
                                [i for i in parms.name()
                                 if not i.isdigit()]
                                ).split('_')[0] + parm_index
            value_names = parms.menuLabels()[index]

            temp_parm_names.append(key_names)
            temp_lods.append(value_names)

        temp_lod_dict = OrderedDict(
                zip(temp_parm_names, temp_lods)
        )

        step_names = []
        for _, lod_step_name in temp_lod_dict.items():
            for default_step_name in __STEP_SUBNETWORK_NAMES__.values():
                if lod_step_name == default_step_name:
                    step_names.append(lod_step_name)

        last_occurance_lods = []
        for steps in list(set(step_names)):
            max_index = max(
                        index
                        for index, v in enumerate(
                            temp_lod_dict.values()
                        ) if v == steps
            )
            last_occurance_lods.append(
                temp_lod_dict.keys()[max_index]
            )
            last_occurance_lods.append(
                temp_lod_dict.keys()[max_index + 1]
            )
            last_occurance_lods.append(
                temp_lod_dict.keys()[max_index + 2]
            )

        for parm_names, _ in temp_lod_dict.items():
            if parm_names not in last_occurance_lods:
                temp_lod_dict.pop(parm_names)

        self.lod_dict = deepcopy(temp_lod_dict)

    def change_lods(self):

        """
        Lod and display changes manipulated inside specific group of subnetworks.
        All util nodes not having lods wont work with lods. Display changes
        with Any combination of lod change only the display parameter in all level.
        all level indicates the alembic node inside the subnetwork and also
        the nodes in obj context. object merge reference is changed to point the
        new lod basset. The respective objmerge parent sop node and node cache date
        changed to new lod choose by the user.

        Static, util, camera nodes doesnot have lods . The node not having lod menus
        conidered dummy. The display mode is works for those nodes with any combination
        of lod choosed by the user

        Example:
            (matchmove Low Boundingbox) if matchmove subnet have only utils then
            it doesnot have lod menus. as so it omit lod changes, accept display changes
            (Animation high FullGeo) Basset having high lods, menus group entries changed
            to all new lod entries and Full geo applied to all depth level of alembic node

        Asset name, asset path, file path entries changed in the
        respective subnets.
        """

        self.make_lod_dict()
        display = {}

        for nodes in self.shot_builder_node.children():
            for parm, display_info in self.lod_dict.items():
                if self.lod_dict[parm] == nodes.userDataDict()['name']:

                    parms = nodes.parm(
                                '{}_assets'.format(
                                        nodes.userDataDict()['name'].lower()
                                )
                    )
                    for parm_instance in parms.multiParmInstances():
                        if parm_instance.name().startswith(
                                nodes.userDataDict()['name'].lower()
                        ):
                            enable_index = str(0)
                            if parm_instance.eval():
                                enable_index = ''.join(
                                    name for name in parm_instance.name()
                                    if name.isdigit()
                                )

                        if parm_instance.name().startswith('asset_name') and \
                                        enable_index in parm_instance.name():

                            parm_digit = ''.join(name for name in parm if name.isdigit())
                            lod_key = 'lod{}'.format(
                                        ''.join(parm_digit)
                            )

                            display_key = 'display{}'.format(
                                            ''.join(parm_digit)
                            )

                            index = ''.join(
                                name for name in parm_instance.name()
                                if name.isdigit()
                            )

                            display[nodes.userDataDict()['name']] = display_key

                            abc_paths = set()

                            for basset_nodes in nodes.children():

                                basset_name = basset_nodes.userDataDict()['name'].rsplit("_", 1)[0]
                                display_lod = self.lod_dict[display[
                                    nodes.userDataDict()['name']]
                                ]

                                def manip_lod_menu_instance(lod, lod_index):

                                    """
                                    A Inner Hook function which get the lod and lod index to pick
                                    the basset node matching to the lod passed. Unlock the
                                    respective menu instances change the values and relock it
                                    :param lod: Lod name strings
                                    :param lod_index: Lod index low =0, high=2, mid=1
                                    :return:
                                    """
                                    if lod in basset_nodes.userDataDict()['name']:

                                        if basset_name == parm_instance.eval().split('/')[0]:

                                            abc_nodes = [
                                                abc
                                                for sopnode in basset_nodes.children()
                                                for abc in sopnode.children()
                                            ]
                                            for abc_node in abc_nodes:

                                                abc_context_path = abc_node.path().rsplit('/', 1)[0]
                                                dest = abc_context_path.split('/')[-1]

                                                # If loc_abc_import_mode is 1 then ani import hda will
                                                # Exist in the location node for the basset. As so below
                                                # Filter get appropriate file name
                                                if abc_node.type().name() == 'alembic':
                                                    abc_path = abc_node.parm('fileName').eval()
                                                elif 'loc_abc_import_mode' in abc_node.userDataDict():
                                                    abc_path = abc_node.parm('ani_fileName').eval()

                                                if display_lod == 'Full Geometry':
                                                    nodes.parm('display_%s' % index).set(1)
                                                    abc_node.parm('viewportlod').set(0)

                                                elif display_lod == 'Bounding Box':
                                                    nodes.parm('display_%s' % index).set(0)
                                                    abc_node.parm('viewportlod').set(2)

                                                replace_basset_name = basset_name + '/' + \
                                                                      lod + '/' + dest

                                                if abc_node.parent().name() in \
                                                            nodes.parm('asset_name_%s' % index).eval():

                                                    nodes.parm('asset_name_%s' % index).lock(False)
                                                    nodes.parm('asset_name_%s' % index).set(replace_basset_name)
                                                    nodes.parm('asset_name_%s' % index).lock(True)

                                                    nodes.parm('asset_path_%s' % index).lock(False)
                                                    nodes.parm('asset_path_%s' % index).set(abc_context_path)
                                                    nodes.parm('asset_path_%s' % index).lock(True)

                                                    nodes.parm('extension_path_%s' % index).lock(False)
                                                    nodes.parm('extension_path_%s' % index).set(abc_path)
                                                    nodes.parm('extension_path_%s' % index).lock(True)

                                                if nodes.parm('lod_%s' % index).eval() != lod_index:
                                                    self.low_lod_last_temp = nodes.parm('lod_%s' % index).eval()

                                                nodes.parm('lod_%s' % index).set(lod_index)
                                                key_name = nodes.userDataDict()['name'].lower() + \
                                                                        '_' + \
                                                                        basset_name
                                                abc_paths.add(abc_node.path())

                                                if self.low_lod_last_temp != '':
                                                    self.changed_lod_info[key_name] = [
                                                        self.default_lods[int(self.low_lod_last_temp)],
                                                        abc_paths
                                                    ]
                                                else:
                                                    self.changed_lod_info[key_name] = [lod,
                                                                                       abc_paths]

                                if self.lod_dict[lod_key] == 'Low':
                                    manip_lod_menu_instance('Low', 0)

                                elif self.lod_dict[lod_key] == 'Mid':
                                    manip_lod_menu_instance('Mid', 1)

                                elif self.lod_dict[lod_key] == 'High':
                                    manip_lod_menu_instance('High', 2)

                                # Util Nodes display controls enabled Here
                                if 'Mid' not in basset_nodes.userDataDict()['name'] and \
                                        'High' not in basset_nodes.userDataDict()['name'] and \
                                        'Low' not in basset_nodes.userDataDict()['name']:
                                    if basset_nodes.type().name() == 'geo':
                                        for abcnode in basset_nodes.children():
                                            if display_lod == 'Full Geometry':
                                                nodes.parm('display_%s' % index).set(1)
                                                abcnode.parm('viewportlod').set(0)
                                            elif display_lod == 'Bounding Box':
                                                nodes.parm('display_%s' % index).set(0)
                                                abcnode.parm('viewportlod').set(2)
                                    else:
                                        if display_lod == 'Full Geometry':
                                            nodes.parm('display_%s' % index).set(1)
                                            basset_nodes.parm('viewportlod').set(0)
                                            LOD.change_alembic_archieve_display(
                                                basset_nodes.userDataDict()['name'].lower(), 0
                                            )

                                        elif display_lod == 'Bounding Box':
                                            nodes.parm('display_%s' % index).set(0)
                                            basset_nodes.parm('viewportlod').set(2)
                                            LOD.change_alembic_archieve_display(
                                                basset_nodes.userDataDict()['name'].lower(), 2
                                            )

        self.change_lods_in_sop_context()

    @staticmethod
    def check_master_null():

        """ Static function if master null exist or not"""

        master_exist_mode = False
        master_node = object
        for nodes in hou.node('/obj').children():
            if nodes.type().name() == 'null':
                if nodes.userDataDict()['MASTERNULL'] == 'MASTERNULL':
                    master_node = nodes
                    master_exist_mode = True
        return master_exist_mode, master_node

    @staticmethod
    def change_alembic_archieve_display(node_name, lod_index):

        """ Display controls changed by user gonna affect to the alembic archive"""

        master_exist_mode, master_node = LOD.check_master_null()
        if master_exist_mode:
            for connected_nodes in master_node.outputConnections():
                if 'geo_node_name' in connected_nodes.outputNode().userDataDict():
                    if connected_nodes.outputNode().type().name() == 'bfx::alembicarchive::1.0' and \
                            node_name in connected_nodes.outputNode().userDataDict()['geo_node_name']:
                        connected_nodes.outputNode().parm('viewportlod').set(lod_index)
                        connected_nodes.outputNode().parm('reloadGeometry').pressButton()

    def change_lods_in_sop_context(self):

        """Method affects changed lod in the object reference entry and change sop node names"""

        master_exist_mode, master_node = LOD.check_master_null()
        if master_exist_mode:
            for connected_nodes in master_node.outputConnections():
                if 'geo_node_name' in connected_nodes.outputNode().userDataDict():
                    for lod_applied_node_name, abc_node_path in self.changed_lod_info.items():
                        if lod_applied_node_name in \
                                connected_nodes.outputNode().userDataDict()['geo_node_name'] and \
                                abc_node_path[0] in connected_nodes.outputNode().userDataDict()['geo_node_name']:

                            for nodepaths in list(abc_node_path[1]):
                                typename = nodepaths.split('/')[-2]
                                if typename in connected_nodes.outputNode().userDataDict()['geo_node_name']:

                                    if 'High' in nodepaths:
                                        lod = 'High'
                                    elif 'Mid' in nodepaths:
                                        lod = 'Mid'
                                    elif 'Low' in nodepaths:
                                        lod = 'Low'
                                    nodename = lod_applied_node_name + '_' + \
                                               lod + '_' + \
                                               typename

                                    connected_nodes.outputNode().setName(nodename)
                                    connected_nodes.outputNode().setUserData('geo_node_name', nodename)
                                    objmerge = [
                                            objmerge
                                            for objmerge in connected_nodes.outputNode().children()
                                    ][0]
                                    objmerge.parm('objpath1').set(nodepaths)


























