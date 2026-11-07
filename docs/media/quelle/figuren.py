#!/usr/bin/env python3
"""Die fünf Demo-Figuren als SVG (eigene Grafik, MIT). Rendern: docs/media/quelle/rendern.py"""
K = "#2b2140"  # Kontur


def rahmen(inhalt):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="800" height="800">
<defs><filter id="w" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="0" flood-color="{K}" flood-opacity=".18"/></filter></defs>
<g stroke="{K}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round" filter="url(#w)">
<ellipse cx="200" cy="362" rx="118" ry="24" fill="#f3e9d8"/>{inhalt}</g></svg>'''


def augen(x1, x2, y, r=17):
    return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff"/><circle cx="{x+3}" cy="{y+2}" r="{r*.55:.0f}" fill="{K}" stroke="none"/><circle cx="{x+7}" cy="{y-4}" r="4" fill="#fff" stroke="none"/>' for x in (x1, x2))


FUCHS = rahmen(f'''
<path d="M286 300 C356 292 368 214 330 182 C326 232 300 252 262 262 Z" fill="#f28a2e"/>
<path d="M330 182 C346 200 352 226 344 250 C330 236 324 208 330 182 Z" fill="#fff"/>
<path d="M128 356 C118 268 142 214 200 214 C258 214 282 268 272 356 Z" fill="#f28a2e"/>
<path d="M164 356 C158 296 172 262 200 262 C228 262 242 296 236 356 Z" fill="#fff4e4"/>
<path d="M98 56 L152 110 L92 150 Z" fill="#f28a2e"/><path d="M302 56 L248 110 L308 150 Z" fill="#f28a2e"/>
<path d="M108 82 L136 112 L104 132 Z" fill="{K}" stroke="none"/><path d="M292 82 L264 112 L296 132 Z" fill="{K}" stroke="none"/>
<path d="M76 142 C84 86 316 86 324 142 C330 196 262 244 200 254 C138 244 70 196 76 142 Z" fill="#f28a2e"/>
<path d="M200 254 C164 248 120 222 104 178 C136 170 176 188 200 216 C224 188 264 170 296 178 C280 222 236 248 200 254 Z" fill="#fff4e4"/>
{augen(150,250,152)}<path d="M186 214 Q200 202 214 214 Q208 230 200 230 Q192 230 186 214 Z" fill="{K}"/>''')

EULE = rahmen(f'''
<path d="M104 200 C62 214 52 276 76 312 C96 300 112 270 118 236 Z" fill="#5b4bb8"/>
<path d="M296 200 C338 214 348 276 324 312 C304 300 288 270 282 236 Z" fill="#5b4bb8"/>
<path d="M100 356 C86 196 112 70 200 70 C288 70 314 196 300 356 Z" fill="#7566d8"/>
<path d="M150 356 C138 280 156 226 200 226 C244 226 262 280 250 356 Z" fill="#f4d9a0"/>
<path d="M172 278 q10 12 20 0 M208 278 q10 12 20 0 M190 316 q10 12 20 0" fill="none"/>
<path d="M112 92 L92 40 L154 74 Z" fill="#7566d8"/><path d="M288 92 L308 40 L246 74 Z" fill="#7566d8"/>
<circle cx="150" cy="150" r="46" fill="#fff"/><circle cx="250" cy="150" r="46" fill="#fff"/>
<circle cx="156" cy="152" r="23" fill="{K}" stroke="none"/><circle cx="244" cy="152" r="23" fill="{K}" stroke="none"/>
<circle cx="164" cy="142" r="7" fill="#fff" stroke="none"/><circle cx="252" cy="142" r="7" fill="#fff" stroke="none"/>
<path d="M186 188 L214 188 L200 216 Z" fill="#f2a52e"/>
<path d="M108 106 q42 -26 84 4 M292 106 q-42 -26 -84 4" fill="none"/>''')

DRACHE = rahmen(f'''
<path d="M270 320 C344 324 372 280 352 232 L330 262 C322 282 300 288 262 280 Z" fill="#3fb37f"/>
<path d="M352 232 L376 214 L368 250 Z" fill="#f2a52e"/>
<path d="M110 232 C54 200 40 142 60 112 C76 142 100 150 128 176 Z" fill="#f2a52e"/>
<path d="M290 232 C346 200 360 142 340 112 C324 142 300 150 272 176 Z" fill="#f2a52e"/>
<path d="M118 356 C106 270 140 210 200 210 C260 210 294 270 282 356 Z" fill="#3fb37f"/>
<path d="M164 356 C156 300 172 256 200 256 C228 256 244 300 236 356 Z" fill="#c9f0d6"/>
<path d="M164 296 h72 M160 326 h80" fill="none"/>
<path d="M132 76 L118 30 L168 60 Z" fill="#f2a52e"/><path d="M268 76 L282 30 L232 60 Z" fill="#f2a52e"/>
<path d="M84 150 C84 84 138 56 200 56 C262 56 316 84 316 150 C316 214 262 240 200 240 C138 240 84 214 84 150 Z" fill="#3fb37f"/>
{augen(150,250,132,19)}
<path d="M138 188 Q200 232 262 188 Q200 204 138 188 Z" fill="#fff"/>
<circle cx="182" cy="172" r="4" fill="{K}" stroke="none"/><circle cx="218" cy="172" r="4" fill="{K}" stroke="none"/>''')

ROBO = rahmen(f'''
<path d="M200 66 V30" fill="none"/><circle cx="200" cy="24" r="14" fill="#e8483f"/>
<rect x="60" y="222" width="40" height="86" rx="20" fill="#9fc5e8"/><rect x="300" y="222" width="40" height="86" rx="20" fill="#9fc5e8"/>
<rect x="150" y="318" width="38" height="42" rx="10" fill="#6f9fca"/><rect x="212" y="318" width="38" height="42" rx="10" fill="#6f9fca"/>
<rect x="92" y="206" width="216" height="122" rx="26" fill="#6fa8dc"/>
<rect x="134" y="228" width="132" height="76" rx="14" fill="#fff"/>
<circle cx="168" cy="266" r="20" fill="#f2a52e"/><path d="M204 248 h44 M204 266 h44 M204 284 h28" fill="none"/>
<rect x="74" y="66" width="252" height="146" rx="34" fill="#9fc5e8"/>
<rect x="104" y="92" width="192" height="92" rx="24" fill="{K}" stroke="none"/>
<circle cx="154" cy="136" r="21" fill="#7ff0d4" stroke="none"/><circle cx="246" cy="136" r="21" fill="#7ff0d4" stroke="none"/>
<path d="M176 164 Q200 180 224 164" fill="none" stroke="#7ff0d4"/>''')

IGEL = rahmen(f'''
<path d="M70 300 L50 262 L82 262 L52 222 L92 226 L70 180 L112 192 L100 142 L140 164 L142 114 L178 148 L198 100 L222 146 L258 112 L262 160 L302 138 L294 188 L338 176 L318 226 L356 222 L328 262 L360 262 L338 300 C340 340 300 356 200 356 C100 356 66 340 70 300 Z" fill="#8a5a3c"/>
<path d="M128 356 C112 276 148 216 200 216 C252 216 288 276 272 356 Z" fill="#f4d9b0"/>
{augen(166,234,262,16)}<circle cx="200" cy="304" r="15" fill="{K}"/>
<path d="M176 328 Q200 346 224 328" fill="none"/>
<circle cx="134" cy="296" r="13" fill="#f2a0a0" stroke="none"/><circle cx="266" cy="296" r="13" fill="#f2a0a0" stroke="none"/>
<path d="M246 170 C276 146 310 162 300 198 C280 208 256 198 246 170 Z" fill="#e8483f"/><path d="M250 172 Q276 176 298 196" fill="none" stroke-width="5"/>''')

LOGO = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="1024" height="1024">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff9a3d"/><stop offset="1" stop-color="#e8483f"/></linearGradient></defs>
<rect x="16" y="16" width="480" height="480" rx="112" fill="url(#g)"/>
<g fill="none" stroke="#fff" stroke-width="22" stroke-linecap="round" opacity=".92">
<path d="M338 142 a150 150 0 0 1 0 150"/><path d="M382 104 a206 206 0 0 1 0 226"/></g>
<g stroke="{K}" stroke-width="13" stroke-linejoin="round" stroke-linecap="round">
<path d="M90 150 L140 196 L92 236 Z" fill="#fff"/><path d="M278 150 L228 196 L276 236 Z" fill="#fff"/>
<path d="M78 226 C84 176 284 176 290 226 C294 286 240 330 184 340 C128 330 74 286 78 226 Z" fill="#fff"/>
<path d="M184 340 C152 334 114 312 100 272 C128 264 164 278 184 304 C204 278 240 264 268 272 C254 312 216 334 184 340 Z" fill="#ffe2b8"/>
<circle cx="140" cy="240" r="15" fill="{K}"/><circle cx="228" cy="240" r="15" fill="{K}"/>
<path d="M172 300 Q184 290 196 300 Q190 314 184 314 Q178 314 172 300 Z" fill="{K}"/></g>
<g fill="#fff"><rect x="96" y="384" width="320" height="30" rx="15" opacity=".95"/><rect x="170" y="424" width="172" height="22" rx="11" opacity=".7"/></g></svg>'''

ALLE = {"fuchs": FUCHS, "eule": EULE, "drache": DRACHE, "robo": ROBO, "igel": IGEL}
