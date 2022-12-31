
A Shot Builder HDA collects and loads all the latest versions of the alembic files from each departments of a shot with available lods and also build related sop nodes in the obj level inside houdini. 

 

Shot builder do several tasks:

- Build or initialize(partially load) Shots 
- Pre Roll and post Roll Playback controls
- Changing Lod for Groups(Animation, Matchmove, Layout)
- Updates new basset publishes entries into all downstream stages of inside Shot builder and also in obj context(WIP)
 

A houdini fx user can able to build a shot using two ways . 

When creating sop nodes in the obj context few concepts are taken in to count. 

1. Step(department) Precedence
2. LOD precedence.  

Step precedence plays which step took priority to the other existing one. if project preset configured with "ani>lay>mmd", 'ani' took first priority than 'lay'. If same basset exist in 'ani' and 'lay', layout subnetwork basset menu entry for that basset is disabled and 'ani' basset menu is enabled.  Lod precedence on the other hand, if a basset has 'Low', 'Mid, 'High' lods, only the 'Low' Lod is loaded in the respective 
subnetwork menu. Bassets succeeding the lod and step precedence is allowed to loading in to the obj context.

'Build Shot' 
    - Create all the step sub-networks related to the shot inside shot builder HDA and creates sop nodes inside object context having object merge node referencing the individual bassets. 

'Init Shot'
    - A partial loader which creates only all step sub-networks. Not sop nodes. User can able to select bassets in the step subnetworks and build the shot in the object context

'Update basset'
    - Push button trigger's the inhouse publisher gui framework, shows all the new published bassets that not already included in the houdini shot context. Artist can able to select more than one basset and load into the scene file.

