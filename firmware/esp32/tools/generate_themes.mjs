import {themeStyle,themeNames,accentNames} from '../../../web/src/themes.js'
import {writeFileSync,readFileSync} from 'node:fs'
const keys=['ground','ink','muted','track','raised','accent','secondary','warning']
let out='// Generated from web/src/themes.js. Run node firmware/esp32/tools/generate_themes.mjs\n#pragma once\n#include <stdint.h>\ntypedef struct {uint32_t '+keys.join(',')+';} screen_palette;\n'
out+='static const char *const screen_theme_names[]={'+themeNames.map(n=>JSON.stringify(n)).join(',')+'};\n'
out+='static const char *const screen_accent_names[]={'+accentNames.map(n=>JSON.stringify(n)).join(',')+'};\n'
out+='static const screen_palette screen_palettes[4][4]={\n'
for(const theme of themeNames){out+=' {';out+=accentNames.map(accent=>{const css=themeStyle({theme,accent});return '{'+keys.map(k=>'0x'+css['--'+k].slice(1)).join(',')+'}'}).join(',');out+='},\n'}
out+='};\n'
const file=new URL('../main/theme_tokens.h',import.meta.url)
if(process.argv.includes('--check')){if(readFileSync(file,'utf8')!==out)throw Error('Firmware theme tokens differ from web themes');console.log('PASS: firmware theme tokens match web themes')}else writeFileSync(file,out)
