from .build_init_shot import (DestroyNillCachedNodesConnected,
                              ModifyIdenticalNameNodes,
                              __TASK_CONTEXT__)
from bfx.api import create_burl
from bfx_hou.utils import node_operation
import hou


class BuildUserSelectedAssets:

    """
    Each Step subnetwork inside shot builder have push buttons 'Update' and
    'Build Selected Asset'. It composed with call back script which trigger
    this class.

    The class responsible of 'Build Selected Asset'. Create the nodes in the obj
    context with object merge referenced the original alembic node path where it
    resides from.

    """
    def __init__(self, sub_node):
        self.sub_node = sub_node
        self.created_nodes = set()
        self.__build()

    @staticmethod
    def create_master_null():

        """ Create master null if not exist"""

        master_null_exist = 0
        for nodes in hou.node('/obj').children():
            if nodes.userDataDict():
                if 'MASTERNULL' in nodes.userDataDict() and \
                        nodes.userDataDict()['MASTERNULL'] == 'MASTERNULL':
                    master_null_exist = 1
                    master_nullnode = nodes

        if not master_null_exist:
            master_nullnode = hou.node("/obj").createNode('null')

            if 'MASTER_NULL' in [node.name() for node in hou.node('/obj').children()]:
                modifynodes = ModifyIdenticalNameNodes('MASTER_NULL')
                modifynodes.modify()

            master_nullnode.setName('MASTER_NULL')
            master_nullnode.setUserData('MASTERNULL', 'MASTERNULL')

        return master_nullnode

    def __build(self):

        """
        Build sop node network for user selected menu instance bassets
        Connect it to master null node and produce gui pop up to the user
        """

        master_nullnode = BuildUserSelectedAssets.create_master_null()
        lowercase_subnet_name = self.sub_node.userDataDict()['name'].lower()
        parm_instances_grp = self.sub_node.parm('{}_assets'.format(lowercase_subnet_name))

        for parms in parm_instances_grp.multiParmInstances():
            if not parms.name().startswith('lod'):
                if parms.eval() == 1:
                    index = parms.name().split('_')[-1]

                    geo_node_name = "{}_{}".format(
                        self.sub_node.userDataDict()['name'].lower(),
                        self.sub_node.parm('asset_name_%s' % index).eval().replace('/', '_')
                    )

                    geo_asset_path = self.sub_node.parm('asset_path_%s' % index).eval()

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
                        file_path = self.sub_node.parm('extension_path_%s' % index).eval()
                        node_type = hou.node(geo_asset_path).type().name()

                    if node_type == 'alembic' or loc_abc_import_mode:

                        create_alembic_node = 0
                        for nodes in hou.node('/obj').children():
                            if nodes.userDataDict():
                                if 'geo_node_name' in nodes.userDataDict():
                                    if nodes.userDataDict()['geo_node_name'] == geo_node_name:
                                        create_alembic_node = 1

                        if not create_alembic_node:
                            get_unchached_nodes = DestroyNillCachedNodesConnected(master_nullnode)
                            get_unchached_nodes.destroy()

                            geo_nodes = hou.node("/obj").createNode('geo')

                            if geo_node_name in [node.name() for node in hou.node('/obj').children()]:
                                modifynodes = ModifyIdenticalNameNodes(geo_node_name)
                                modifynodes.modify()

                            geo_nodes.setName(geo_node_name)
                            geo_nodes.setUserData('geo_node_name', geo_node_name)
                            geo_nodes.setUserData('geo_asset_path', geo_asset_path)
                            geo_nodes.setColor(hou.Color((0.71, 0.784, 1)))
                            self.created_nodes.add(geo_nodes)
                            object_merge_node = geo_nodes.createNode('object_merge')
                            object_merge_node.parm('xformtype').set(1)
                            object_merge_node.parm('objpath1').set(alembic_node.path())

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

                            geo_nodes.setInput(0, master_nullnode)

                    elif node_type == 'alembicarchive':

                        create_alembic_archeive = 0
                        for nodes in hou.node('/obj').children():
                            if nodes.userDataDict():
                                if 'geo_node_name' in nodes.userDataDict():
                                    if nodes.userDataDict()['geo_node_name'] == geo_node_name:
                                        create_alembic_archeive = 1

                        if not create_alembic_archeive:
                            get_unchached_archieve_nodes = DestroyNillCachedNodesConnected(master_nullnode)
                            get_unchached_archieve_nodes.destroy()

                            alembic_archive_node = node_operation.create_archive(file_path,
                                                                                 show=__TASK_CONTEXT__.show_name,
                                                                                 burl=create_burl(file_path),
                                                                                 toggled=1)

                            if geo_node_name in [node.name() for node in hou.node('/obj').children()]:
                                modifynodes = ModifyIdenticalNameNodes(geo_node_name)
                                modifynodes.modify()

                            alembic_archive_node.setName(geo_node_name)
                            alembic_archive_node.setUserData('geo_node_name', geo_node_name)
                            alembic_archive_node.setUserData('geo_asset_path', geo_asset_path)
                            alembic_archive_node.setColor(hou.Color((0.565, 0.494, 0.863)))
                            self.created_nodes.add(alembic_archive_node)
                            alembic_archive_node.setInput(0, master_nullnode)


        for nodes in hou.node('/obj').children():
            if nodes.userDataDict():
                if 'MASTERNULL' not in nodes.userDataDict():
                    if 'geo_node_name' in nodes.userDataDict():
                        nodes.setInput(0, master_nullnode)

        if list(self.created_nodes):
            msg = 'Following Nodes Were Created inside /obj\n\n'
            for nodes in list(self.created_nodes):
                msg += nodes.name() + '\n'
            hou.ui.displayMessage("{}".format(msg),
                                  title='Shot Builder')

            self.created_nodes.add(master_nullnode)

            hou.node("/obj").layoutChildren(
                items=[node for node in list(self.created_nodes)],
                horizontal_spacing=2,
                vertical_spacing=1
            )

class UpdateMenus:

    """
    Each Step subnetwork inside shot builder have push buttons 'Update' and
    'Build Selected Asset'. It composed with call back script which trigger
    this class.

    The class responsible of 'Update' push button. mainly works for
    changing lods and display controls.It update user selected changes in the
    respective menus instance and also in the object merge node references
    if the specific basset exist in the sop node context.
    """

    def __init__(self, sub_node):

        self.sub_node = sub_node
        self.default_lods = {0: 'Low', 1: 'Mid', 2: 'High'}
        self.lod_dict = {}
        self.basset_lod_dict = {}
        self.abc_list = set()

    def update_display(self):

        """
        Unlock and change asset menu instance parameter entries based upon user
        selection and lock the menu instance again.
        """
        loaded_parms = set()
        current_parms = set()
        current_asset_paths = set()
        parms = self.sub_node.parm(
            '{}_assets'.format(
                self.sub_node.userDataDict()['name'].lower()
            )
        )
        for parm_instance in parms.multiParmInstances():
            if parm_instance.name().startswith('lod'):
                lod_parm_index = [num for num in parm_instance.name() if num.isdigit()][0]
                lod_value_txt = self.default_lods[parm_instance.eval()]
                self.lod_dict[lod_parm_index] = lod_value_txt

        for num, lod in self.lod_dict.items():
            for parm_instance in parms.multiParmInstances():
                if parm_instance.name().startswith('asset_name'):
                    if num in parm_instance.name():
                        self.basset_lod_dict[parm_instance.name()] = lod

        for parmeter,lod in self.basset_lod_dict.items():
            for parm_instance in parms.multiParmInstances():
                if parm_instance.name() == parmeter:
                    index = ''.join(parm_digit
                                    for parm_digit in parm_instance.name()
                                    if parm_digit.isdigit()
                                    )
                    if not self.sub_node.parm('lod_%s' %index).isHidden() and \
                            self.sub_node.parm('%s_import_%s' %(
                                    self.sub_node.userDataDict()['name'].lower(),
                                    index)).eval():

                        loaded_parms.add(parm_instance.eval())

                        index = [num for num in parmeter if num.isdigit()][0]
                        extract_basset_name = parm_instance.eval().split('/')[0]
                        extract_basset_type = parm_instance.eval().split('/')[-1]
                        extract_lod_basset_name = extract_basset_name + '_' + lod
                        extract_lod_node = "/obj/"+ self.sub_node.parent().name() + \
                                           '/' + self.sub_node.name() + \
                                           '/' + extract_lod_basset_name + \
                                           '/' + extract_basset_type

                        # Check if user finding specific lod node exist
                        if hou.node(extract_lod_node):
                            abc_nodes = [nodes for nodes in  hou.node(extract_lod_node).children()]

                            for abc_node in abc_nodes:
                                # If loc_abc_import_mode is 1 then ani import hda will
                                # Exist in the location node for the basset. As so below
                                # Filter get appropriate file name
                                if abc_node.type().name() == 'alembic':
                                    file_name = abc_node.parm('fileName').eval()
                                elif 'loc_abc_import_mode' in abc_node.userDataDict():
                                    file_name = abc_node.parm('ani_fileName').eval()

                                abc_context_path = abc_node.path().rsplit('/', 1)[0]
                                dest = abc_context_path.split('/')[-1]

                                replace_basset_name = extract_basset_name + '/' + \
                                                    lod + '/' + dest

                                self.sub_node.parm('asset_name_%s' %index).lock(False)
                                self.sub_node.parm('asset_path_%s' % index).lock(False)
                                self.sub_node.parm('extension_path_%s' % index).lock(False)
                                self.sub_node.parm('asset_name_%s' % index).set(replace_basset_name)
                                self.sub_node.parm('asset_path_%s' % index).set(abc_context_path)
                                self.sub_node.parm('extension_path_%s' % index).set(file_name)
                                self.sub_node.parm('asset_name_%s' % index).lock(True)
                                self.sub_node.parm('asset_path_%s' % index).lock(True)
                                self.sub_node.parm('extension_path_%s' % index).lock(True)

                                display = self.sub_node.parm('display_%s' %index).eval()
                                if display == 0:
                                    abc_node.parm('viewportlod').set(2)
                                elif display == 1:
                                    abc_node.parm('viewportlod').set(0)

                                current_parms.add(parm_instance.eval())
                                current_asset_paths.add(
                                    self.sub_node.parm('asset_path_%s' % index).eval())

                        else:
                            asset_name = self.sub_node.parm('asset_name_%s' % index).eval()
                            prev_lod = self.sub_node.parm('asset_name_%s' % index).eval().split('/')[1]
                            self.sub_node.parm('lod_%s' % index).set(prev_lod)

                            hou.ui.displayMessage("{} not have Lod \"{}\"\n Falling back to \"{}\"".format(
                                                                                    asset_name,
                                                                                    lod,
                                                                                    prev_lod),
                                                  title='Shot Builder')

                    # Display options changes for all camera and util nodes
                    # For cameras it update the display inside subnet and also if
                    # alembic archive exist in the /obj context
                    elif self.sub_node.parm('lod_%s' %index).isHidden() and  \
                                                        self.sub_node.parm('%s_import_%s' %(
                                                        self.sub_node.userDataDict()['name'].lower(),
                                                        index)).eval():
                        util_nodes = []
                        index = [num for num in parmeter if num.isdigit()][0]
                        extract_basset_name = parm_instance.eval()
                        extract_node = "/obj/" + self.sub_node.parent().name() + \
                                            '/' + self.sub_node.name() + '/' + extract_basset_name

                        if hou.node(extract_node).type().name() == 'geo':
                            for nodes in hou.node(extract_node).children():
                                util_nodes.append(nodes)
                        elif hou.node(extract_node).type().name() == 'alembicarchive':
                            util_nodes.append(hou.node(extract_node))

                        for abc_node in util_nodes:
                            display = self.sub_node.parm('display_%s' % index).eval()
                            if display == 0:
                                abc_node.parm('viewportlod').set(2)
                            elif display == 1:
                                abc_node.parm('viewportlod').set(0)

                        # Update in /obj if exist
                        for nodes in hou.node('/obj').children():
                            if nodes.userDataDict():
                                if 'geo_node_name' in nodes.userDataDict():
                                    if extract_basset_name in nodes.userDataDict()['geo_node_name']:
                                        if display == 0:
                                            nodes.parm('viewportlod').set(2)
                                        elif display == 1:
                                            nodes.parm('viewportlod').set(0)

        new_parm = current_parms - loaded_parms
        new_parm_names = [new_parm_name.replace('/', '_') for new_parm_name in list(new_parm)]

        intersect_parm_names = [v.replace('/', '_') for v in list(loaded_parms)
                          if v not in list(current_parms)
                          ]

        combination_parameters = {}
        for intersect_name in intersect_parm_names:
            for new_parm_name in new_parm_names:
                for current_asset_path in current_asset_paths:
                    node_path = {}
                    if intersect_name.split('_')[-1] in new_parm_name:
                            type_name = new_parm_name.rsplit('_', 1)[-1]
                            orig_name = new_parm_name.rsplit('_',1)[0] + '/' + type_name
                            if orig_name in current_asset_path:
                                node_path[new_parm_name] = current_asset_path
                                combination_parameters[intersect_name] = node_path

        for nodes in hou.node('/obj').children():
            if nodes.userDataDict():
                if 'geo_node_name' in nodes.userDataDict():

                    for old_node_name, new_node_name in combination_parameters.items():
                        found_node = self.sub_node.userDataDict()['name'].lower() + \
                                     '_' + \
                                     old_node_name
                        if nodes.userDataDict()['geo_node_name'] == found_node:

                            for new_node_names, new_node_path in new_node_name.items():

                                set_new_node_name = self.sub_node.userDataDict()['name'].lower() +  \
                                            '_' + new_node_names
                                nodes.setName(set_new_node_name)
                                nodes.setUserData('geo_node_name', set_new_node_name)

                                extract_basset = new_node_path.split('/')[-2]
                                new_node_path = new_node_path + '/' + extract_basset
                                objmerge = [obj_merge for obj_merge in nodes.children()
                                            if obj_merge.type().name() == 'object_merge'
                                            ][0]
                                objmerge.parm('objpath1').set(new_node_path)










