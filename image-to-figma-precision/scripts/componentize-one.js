// Embed after: const config = {pageId, rootId, shelfId, sourceId, key,
//   componentKeys: [...all component keys], stableKeys: [...all manifest keys]};
// One completed FRAME per call. Persist returned mapping before next call.
const page = await figma.getNodeByIdAsync(config.pageId);
await figma.setCurrentPageAsync(page);
const [root, shelf, source] = await Promise.all([
  figma.getNodeByIdAsync(config.rootId), figma.getNodeByIdAsync(config.shelfId),
  figma.getNodeByIdAsync(config.sourceId)
]);
if (!root || !shelf || !source) throw new Error('Missing root, shelf or source; refresh state');
const descendants = n => [n, ...('findAll' in n ? n.findAll(() => true) : [])];
const inRoot = descendants(root);
// Intrinsic layers of repeated icon instances may share names; they are not
// stable manifest keys and must not invalidate a completed parent conversion.
const nameCounts=new Map();for(const n of inRoot)nameCounts.set(n.name,(nameCounts.get(n.name)||0)+1);
const stable=new Set(config.stableKeys||inRoot.filter(n=>nameCounts.get(n.name)===1).map(n=>n.name));
if (!inRoot.some(n => n.id === source.id)) throw new Error('Source is outside the owned reconstruction root');
if (inRoot.some(n => n.id === shelf.id)) throw new Error('Component shelf must be outside the reconstruction');
if (shelf.type !== 'FRAME' || shelf.layoutMode !== 'NONE') throw new Error('Shelf must be a free-layout FRAME');
if (source.type !== 'FRAME' || source.name !== config.key) throw new Error('Expected exact FRAME key; refresh state before retry');
for (let p=source.parent; p && p!==page; p=p.parent)
  if (p.type==='INSTANCE' || p.type==='COMPONENT') throw new Error('Convert children before parents; source is in a component/instance');
const expected = new Set(config.componentKeys);
const pending = descendants(source).slice(1).filter(n => expected.has(n.name) && n.type==='FRAME');
if (pending.length) throw new Error('Unconverted child components: '+pending.map(n=>n.name).join(', '));
const duplicateKeys = inRoot.map(n=>n.name).filter((name,i,a)=>expected.has(name)&&a.indexOf(name)!==i);
if (duplicateKeys.length) throw new Error('Ambiguous component keys in root: '+duplicateKeys.join(', '));
const fonts = new Map();
for (const n of descendants(source).filter(n=>n.type==='TEXT'))
  for (const segment of n.getStyledTextSegments(['fontName']))
    fonts.set(segment.fontName.family+'\0'+segment.fontName.style,segment.fontName);
await Promise.all([...fonts.values()].map(f=>figma.loadFontAsync(f)));
const parent=source.parent, index=parent.children.indexOf(source);
const original={x:source.x,y:source.y,width:source.width,height:source.height,
  rotation:source.rotation,layoutPositioning:source.layoutPositioning,
  layoutSizingHorizontal:source.layoutSizingHorizontal,layoutSizingVertical:source.layoutSizingVertical,
  constraints:source.constraints};
const beforeIds=descendants(source).map(n=>n.id);
// Moving this exact owned draft preserves its children; no fuzzy-name cleanup.
shelf.appendChild(source);
const main=figma.createComponentFromNode(source);
main.name=config.key;
main.description='Image reconstruction component. Background, artwork and native text remain separate. Source key: '+config.key;
main.x=24;main.y=Math.max(0,...shelf.children.filter(n=>n.id!==main.id).map(n=>n.y+n.height))+24;
shelf.resize(Math.max(shelf.width,main.x+main.width+24),Math.max(shelf.height,main.y+main.height+24));
// Expose direct text descendants; text owned by nested instances stays governed
// by its own main component, rather than being rewritten through an instance.
const textProperties={};
for (const t of descendants(main).filter(n=>n.type==='TEXT')) {
  let owned=true;
  for(let p=t.parent;p&&p!==main;p=p.parent)if(p.type==='INSTANCE')owned=false;
  if(!owned)continue;
  const property=main.addComponentProperty(t.name,'TEXT',t.characters);
  t.componentPropertyReferences={...t.componentPropertyReferences,characters:property};
  textProperties[t.name]=property;
}
const instance=main.createInstance();instance.name=config.key;
parent.insertChild(index,instance);
instance.resize(original.width,original.height);instance.rotation=original.rotation;
if(parent.layoutMode && parent.layoutMode!=='NONE')instance.layoutPositioning=original.layoutPositioning;
instance.x=original.x;instance.y=original.y;instance.constraints=original.constraints;
if(parent.layoutMode && parent.layoutMode!=='NONE' && original.layoutPositioning!=='ABSOLUTE') {
  instance.layoutSizingHorizontal=original.layoutSizingHorizontal;
  instance.layoutSizingVertical=original.layoutSizingVertical;
}
const current=descendants(root),mapping={};
for(const n of current){
  if(n===root){mapping.root=n.id;continue;}
  if(!stable.has(n.name))continue;
  if(mapping[n.name])throw new Error('Duplicate stable key after conversion: '+n.name);
  mapping[n.name]=n.id;
}
const afterIds=new Set([...descendants(main),...descendants(instance)].map(n=>n.id));
figma.commitUndo();
return {key:config.key,mainComponentId:main.id,instanceId:instance.id,textProperties,mapping,
  createdNodeIds:[...afterIds].filter(id=>!beforeIds.includes(id)),
  mutatedNodeIds:[parent.id,shelf.id,...afterIds],
  retiredNodeIds:beforeIds.filter(id=>!afterIds.has(id)),
  requiresValidation:['same geometry and sibling order','screenshot before/after','native text edit','instance property propagation']};
