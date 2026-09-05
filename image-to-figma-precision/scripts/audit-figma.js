// Embed in use_figma, then: return auditFigma(root, manifest);
function auditFigma(root, manifest) {
  const nodes = [root, ...root.findAll(() => true)];
  const byId = new Map(nodes.map(n => [n.id, n]));
  const failures = [];
  const inventory = nodes.map(n => ({id:n.id,name:n.name,type:n.type,
    visible:n.visible,opacity:n.opacity,width:n.width,height:n.height,
    ...(n.type === 'TEXT' ? {characters:n.characters,fontName:n.fontName,hasMissingFont:n.hasMissingFont} : {})}));
  function effectivelyVisible(n) {
    for (let p=n; p && p.type !== 'PAGE'; p=p.parent) {
      if (p.visible === false || p.opacity === 0) return false;
    }
    return true;
  }
  for (const t of manifest.texts || []) {
    const n=byId.get(t.nodeId);
    if (!n || n.type !== 'TEXT') failures.push({key:t.key,reason:'missing_native_text'});
    else {
      if (n.characters !== t.characters) failures.push({key:t.key,reason:'wrong_characters',actual:n.characters});
      if (!effectivelyVisible(n)) failures.push({key:t.key,reason:'hidden_text'});
      if (n.hasMissingFont) failures.push({key:t.key,reason:'missing_font'});
    }
  }
  for (const e of manifest.elements || []) {
    const n=byId.get(e.nodeId);
    if (!n) failures.push({key:e.key,reason:'missing_element'});
    else if (e.role === 'component' && !['COMPONENT','INSTANCE'].includes(n.type))
      failures.push({key:e.key,reason:'not_component_or_instance'});
  }
  for (const n of nodes) {
    if (!(n.width>0 && n.height>0)) failures.push({id:n.id,reason:'zero_geometry'});
    if (n.placeholder) failures.push({id:n.id,reason:'unfinished_placeholder'});
  }
  return {rootId:root.id,nodeCount:nodes.length,textCount:nodes.filter(n=>n.type==='TEXT').length,
    componentCount:nodes.filter(n=>['COMPONENT','INSTANCE'].includes(n.type)).length,
    failures,inventory,requiresVisualReview:['baked_text','clip_and_occlusion','font_visual_match','mask_edges']};
}
