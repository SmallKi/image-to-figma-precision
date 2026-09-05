// Input literals supplied by orchestrator: batch, state, positions, colors, assets.
// Validate the full batch before any Figma mutation.
for(const s of batch){
 if(s.requiresTransparency && (s.crop || !s.transparentAsset))throw new Error('Transparent foreground is not ready: '+s.key);
 if(s.transparentAsset){
  const a=assets[s.transparentAsset];
  if(s.crop || !a?.imageHash || !a.sha256 || a.alphaReport?.rawGate!=='pass' || !a.alphaReport.hasAlpha || a.alphaReport.sourceSha256!==a.sha256 || a.visualReview?.status!=='pass' || !['white','black','magenta'].every(c=>a.visualReview.backgrounds?.includes(c)) || !['smoothEdges','noMatte','highlightsPreserved','holesCorrect'].every(k=>a.visualReview.checks?.[k]==='pass') || (a.semanticContract && (a.semanticReport?.pass!==true || a.semanticReport?.imageSha256!==a.sha256)))throw new Error('Unverified transparent asset: '+s.key);
 }
}
const page=await figma.getNodeByIdAsync(config.pageId);
await figma.setCurrentPageAsync(page);
const createdNodeIds=[],mutatedNodeIds=[],mapping={};
const colorVars={};for(const [hex,id] of Object.entries(colors))colorVars[hex]=await figma.variables.getVariableByIdAsync(id);
const rgb=h=>({r:parseInt(h.slice(1,3),16)/255,g:parseInt(h.slice(3,5),16)/255,b:parseInt(h.slice(5,7),16)/255});
function solid(h){let p={type:'SOLID',color:rgb(h)};if(colorVars[h])p=figma.variables.setBoundVariableForPaint(p,'color',colorVars[h]);return p;}
const fonts=[...new Map(batch.filter(s=>s.type==='TEXT').map(s=>[s.family+'|'+s.style,{family:s.family,style:s.style}])).values()];
await Promise.all(fonts.map(f=>figma.loadFontAsync(f)));
for(const s of batch){
 if(state[s.key])continue;
 const parent=await figma.getNodeByIdAsync(mapping[s.parent]||state[s.parent]);
 if(!parent)throw new Error('Missing parent '+s.parent);
 const node=s.type==='TEXT'?figma.createText():['COMPONENT','FRAME'].includes(s.type)?figma.createFrame():s.type==='VECTOR'?figma.createVector():figma.createRectangle();
 createdNodeIds.push(node.id);parent.appendChild(node);mutatedNodeIds.push(parent.id);
 node.name=s.key;node.resize(s.box[2],s.box[3]);node.x=s.box[0]-positions[s.parent][0];node.y=s.box[1]-positions[s.parent][1];
 node.fills=[];
 node.strokes=[];
 if(s.type==='COMPONENT'){node.clipsContent=false;}
 if(s.path)node.vectorPaths=[{windingRule:'NONZERO',data:s.path}];
 if(s.radius)node.cornerRadius=s.radius;
 if(s.color)node.fills=[solid(s.color)];
 if(s.gradient)node.fills=[{type:'GRADIENT_LINEAR',gradientTransform:[[0,1,0],[-1,0,1]],gradientStops:s.gradient.map((h,i)=>({position:i/(s.gradient.length-1),color:{...rgb(h),a:1}}))}];
 if(s.crop){const [x,y,w,h]=s.crop;node.fills=[{type:'IMAGE',imageHash:config.sourceHash,scaleMode:'CROP',imageTransform:[[w/config.sourceWidth,0,x/config.sourceWidth],[0,h/config.sourceHeight,y/config.sourceHeight]]}];}
 if(s.transparentAsset){node.fills=[{type:'IMAGE',imageHash:assets[s.transparentAsset].imageHash,scaleMode:'FILL'}];}
 if(s.stroke){node.strokes=[solid(s.stroke)];node.strokeWeight=s.sw||1;node.strokeAlign='INSIDE';}
 if(s.shadow)node.effects=[{type:'DROP_SHADOW',color:{r:.3,g:.23,b:.12,a:.22},offset:{x:0,y:s.shadow},radius:4,visible:true,blendMode:'NORMAL'}];
 if(s.type==='TEXT'){
   node.fontName={family:s.family,style:s.style};node.fontSize=s.size;
   node.characters=s.text;node.lineHeight={unit:'PIXELS',value:s.box[3]};node.textAutoResize='NONE';node.resize(s.box[2],s.box[3]);node.textAlignHorizontal=s.align||'LEFT';node.textAlignVertical='CENTER';
   if(s.outline){node.strokes=[solid(s.outline)];node.strokeWeight=s.outlineWidth;node.strokeAlign='OUTSIDE';}
 }
 mapping[s.key]=node.id;
}
figma.commitUndo();
return {createdNodeIds,mutatedNodeIds:[...new Set(mutatedNodeIds)],mapping};
