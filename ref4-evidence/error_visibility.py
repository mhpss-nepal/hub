from pathlib import Path
p=Path(__file__).resolve().parents[1]/'index.html';s=p.read_text()
old="  syncEntry();\n  function observeBridge(){"
new="""  syncEntry();
  /* A live access result must not disappear inside the compact disclosure. */
  var livePanel=document.getElementById('livePanel');
  function revealAccess(){if(!livePanel.hidden && !document.getElementById('loader').hidden)document.getElementById('access-options').open=true;}
  new MutationObserver(revealAccess).observe(livePanel,{attributes:true,attributeFilter:['hidden'],childList:true,subtree:true});
  revealAccess();
  function observeBridge(){"""
assert old in s;s=s.replace(old,new,1);p.write_text(s)
print('live access/errors open disclosure without changing runtime/auth')
