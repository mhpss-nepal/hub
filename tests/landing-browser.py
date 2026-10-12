"""Explicit synthetic account/API fixtures, never production proof."""
import json, threading, http.server, functools
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}'
checks=[]
def check(name,value):
 checks.append({'name':name,'pass':bool(value)});assert value,name
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 for width in [390,1280]:
  page=browser.new_page(viewport={'width':width,'height':900})
  page.route('https://www.gstatic.com/**',lambda route:route.abort())
  page.goto(origin+'/')
  check(f'{width} six task cards',page.locator('#landing .card').count()==6)
  check(f'{width} no role simulation',page.locator('#demoRole').count()==0)
  check(f'{width} no overflow',page.evaluate('document.documentElement.scrollWidth===innerWidth'))
  page.locator('[data-view="forms"]').first.click()
  check(f'{width} canonical form directory',page.locator('#formList a[href="../form/5ws-report.html"]').count()==1)
  check(f'{width} no routine developer reader',page.locator('#formList a[href*="review-current"]').count()==0)
  page.screenshot(path=str(ROOT/'landing-evidence'/f'signedout-{width}.png'),full_page=True)
  page.close()
 browser.close()
server.shutdown()
print(json.dumps({'fixture':True,'production_access':False,'checks':checks},indent=2))
