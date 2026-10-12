/* Explicit legacy modes only. Never route an email action away from Auth. */
(function(){'use strict';var q=new URLSearchParams(location.search),keys=[...q.keys()],actions=['mode','oobCode','apiKey','continueUrl','lang','tenantId'];
 if(!keys.some(k=>actions.includes(k))&&keys.every(k=>k==='source')&&keys.length===1&&['demo','choose','live','historical'].includes(q.get('source'))){location.replace('legacy-dashboard.html'+location.search+location.hash);return;}
 var view=q.get('view'),allowed=['register','login','entries','forms','guide','dashboard'];
 window.STAFF_AUTH_RETURN=location.origin+location.pathname+'?view='+(allowed.includes(view)?view:'login');
})();
