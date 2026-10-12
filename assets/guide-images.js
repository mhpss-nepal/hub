/* Enlarge only the guide's fixed, same-origin image references. */
(function(){'use strict';let trigger=null;const dialog=document.getElementById('guide-image-dialog');if(!dialog)return;const large=document.getElementById('guide-image-large');
function open(image){trigger=image;large.src=image.src;large.alt=image.alt;document.getElementById('guide-image-title').textContent=image.closest('li').querySelector('h2').textContent;dialog.showModal();document.getElementById('guide-image-close').focus();}
document.querySelectorAll('#guide .guide-step figure>img').forEach(image=>{image.addEventListener('click',()=>open(image));image.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();open(image);}});});
document.getElementById('guide-image-close').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{large.removeAttribute('src');if(trigger)trigger.focus();});
})();