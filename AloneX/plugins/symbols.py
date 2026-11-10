from pyrogram import filters, types, enums
from AloneX import pbot as bot, font


__module__ = "𝐒ʏᴍʙᴏʟs✨"

__help__ = """
*Symbols✨*

*Description:*  
Get a collection of symbols to use in games, usernames, or anywhere you like. 46 symbol types available!

*Commands:*  
❂ `/symbols` – Display your favorite symbols

*Example:*  
`/symbols`
"""


data = {
    "Stars Symbols": "★\n☆\n✡\n✦\n✧\n✩\n✪\n✫\n✬\n✭\n✮\n✯\n✰\n⁂\n⁎\n⁑\n✢\n✣\n✤\n✥\n✱\n✲\n✳\n✴\n✵\n✶\n✷\n✸\n✹\n✺\n✻\n✼\n✽\n✾\n✿\n❀\n❁\n❂\n❃\n❇\n❈\n❉\n❊\n❋\n❄\n❆\n❅\n⋆\n≛\nᕯ\n✲\n࿏\n꙰ \n۞\n⭒\n⍟\n⭐\n🌠\n🌟\n💫\n✨\n🌃\n🔯",
    "Copyright, Trademark, Office & Law Symbols": "©\n®\n™\n℠\n℡\n℗\n‱\n№\n℀\n℁\n℅\n℆\n⅍\n☊\n☎\n☏\n⌨\n✁\n✂\n✃\n✄\n✆\n✇\n✈\n✉\n✎\n✏\n✐\n✑\n✒\n‰\n§\n¶\n✌️\n☝️\n☞\n☛\n☟\n☜\n☚\n✍️",
    "Currency Symbols - Cent, Dollar, Euro... Symbols": "¢\n$\n€\n£\n¥\n₮\n৲\n৳\n௹\n฿\n៛\n₠\n₡\n₢\n₣\n₤\n₥\n₦\n₧\n₨\n₩\n₪\n₫\n₭\n₯\n₰\n₱\n₲\n₳\n₴\n₵\n￥\n﷼\n¤\nƒ",
    "Bracket Symbols": "〈\n〉\n《\n》\n「\n」\n『\n』\n【\n】\n〔\n〕\n︵\n︶\n︷\n︸\n︹\n︺\n︻\n︼\n︽\n︾\n︿\n﹀\n﹁\n﹂\n﹃\n﹄\n﹙\n﹚\n﹛\n﹜\n﹝\n﹞\n﹤\n﹥\n（\n）\n＜\n＞\n｛\n｝\n〖\n〗\n〘\n〙\n〚\n〛\n«\n»\n‹\n›\n〈\n〉\n〱",
    "Chess & Card Symbols": "♔\n♕\n♖\n♗\n♘\n♙\n♚\n♛\n♜\n♝\n♞\n♟\n♤\n♠\n♧\n♣\n♡\n♥\n♢\n♦",
    "Musical Notes & Music Symbols": "♩\n♪\n♫\n♬\n♭\n♮\n♯\n°\nø\n؂\n≠\n≭",
    "Degree, Weather & Unit Symbols": "°\n℃\n℉\nϟ\n☀\n☁\n☂\n☃\n☉\n☼\n☽\n☾\n♁\n♨\n❄\n❅\n❆\n☇\n☈\n☄\n㎎\n㎏\n㎜\n㎝\n㎞\n㎡\n㏄\n㏎\n㏑\n㏒\n㏕",
    "Arrows Symbols": "↕\n↖\n↗\n↘\n↙\n↚\n↛\n↜\n↝\n↞\n↟\n↠\n↡\n↢\n↣\n↤\n↥\n↦\n↧\n↨\n↩\n↪\n↫\n↬\n↭\n↮\n↯\n↰\n↱\n↲\n↳\n↴\n↶\n↷\n↸\n↹\n↺\n↻\n↼\n↽\n↾\n↿\n⇀\n⇁\n⇂\n⇃\n⇄\n⇅\n⇆\n⇇\n⇈\n⇉\n⇊\n⇋\n⇌\n⇍\n⇎\n⇏\n⇕\n⇖\n⇗\n⇘\n⇙\n⇚\n⇛\n⇜\n⇝\n⇞\n⇟\n⇠\n⇡\n⇢\n⇣\n⇤\n⇥\n⇦\n⇧\n⇨\n⇩\n⇪\n⌅\n⌆\n⌤\n⏎\n▶\n☇\n☈\n☊\n☋\n☌\n☍\n➔\n➘\n➙\n➚\n➛\n➜\n➝\n➞\n➟\n➠\n➡\n➢\n➣\n➤\n➥\n➦\n➧\n➨\n➩\n➪\n➫\n➬\n➭\n➮\n➯\n➱\n➲\n➳\n➴\n➵\n➶\n➷\n➸\n➹\n➺\n➻\n➼\n➽\n➾\n⤴\n⤵\n↵\n↓\n↔\n←\n→\n↑\n⌦\n⌫\n⌧\n⇰\n⇫\n⇬\n⇭\n⇳\n⇮\n⇯\n⇱\n⇲\n⇴\n⇵\n⇷\n⇸\n⇹\n⇺\n⇑\n⇓\n⇽\n⇾\n⇿\n⬳\n⟿\n⤉\n⤈\n⇻\n⇼\n⬴\n⤀\n⬵\n⤁\n⬹\n⤔\n⬺\n⤕\n⬶\n⤅\n⬻\n⤖\n⬷\n⤐\n⬼\n⤗\n⬽\n⤘\n⤝\n⤞\n⤟\n⤠\n⤡\n⤢\n⤣\n⤤\n⤥\n⤦\n⤪\n⤨\n⤧\n⤩\n⤭\n⤮\n⤯\n⤰\n⤱\n⤲\n⤫\n⤬\n⬐\n⬎\n⬑\n⬏\n⤶\n⤷\n⥂\n⥃\n⥄\n⭀\n⥱\n⥶\n⥸\n⭂\n⭈\n⭊\n⥵\n⭁\n⭇\n⭉\n⥲\n⭋\n⭌\n⥳\n⥴\n⥆\n⥅\n⥹\n⥻\n⬰\n⥈\n⬾\n⥇\n⬲\n⟴\n⥷\n⭃\n⥺\n⭄\n⥉\n⥰\n⬿\n⤳\n⥊\n⥋\n⥌\n⥍\n⥎\n⥏\n⥐\n⥑\n⥒\n⥓\n⥔\n⥕\n⥖\n⥗\n⥘\n⥙\n⥚\n⥛\n⥜\n⥝\n⥞\n⥟\n⥠\n⥡\n⥢\n⥤\n⥣\n⥥\n⥦\n⥨\n⥧\n⥩\n⥮\n⥯\n⥪\n⥬\n⥫\n⥭\n⤌\n⤍\n⤎\n⤏\n⬸\n⤑\n⬱\n⟸\n⟹\n⟺\n⤂\n⤃\n⤄\n⤆\n⤇\n⤊\n⤋\n⭅\n⭆\n⟰\n⟱\n⇐\n⇒\n⇔\n⇶\n⟵\n⟶\n⟷\n⬄\n⬀\n⬁\n⬂\n⬃\n⬅\n⬆\n⬇\n⬈\n⬉\n⬊\n⬋\n⬌\n⬍\n⟻\n⟼\n⤒\n⤓\n⤙\n⤚\n⤛\n⤜\n⥼\n⥽\n⥾\n⥿\n⤼\n⤽\n⤾\n⤿\n⤸\n⤺\n⤹\n⤻\n⥀\n⥁\n⟲\n⟳",
    "Astrological & Zodiac Sign Symbols": "☮\n☸\n♈\n♉\n☪\n♊\n♋\n♌\n♍\n♎\n♏\n♐\n♑\n♒\n♓\n☤\n☥\n☧\n☨\n☩\n☫\n☬\n☭\n☯\n☽\n☾\n✙\n✚\n✛\n✜\n✝\n✞\n✟\n†\n⊹\n‡\n♁\n♆\n❖\n♅\n✠\n✡\n✢\n卍\n卐\n〷\n☠\n☢\n☣\n☦",
    "Heart Symbols": "♥\n♡\n❥\n❣\n❦\n❧\nდ\nღ\n۵\nლ\nও\nლ\n❤️️\n💙\n🧡\n💚\n💛\n💜\n🖤\n💗\n💓\n💔\n💟\n💕\n💖\n❣️\n💘\n💝\n💞",
    "Check mark & Tick Symbols": "✓\n✔\n✗\n✘\n☓\n∨\n√\n✔️\n✅\n❎\n❌\n💯\n✇\n☐\n☑\n☒\n〤\n〥",
    "Male, Female, People & Smiley Symbols": "♀\n♂\n☹\n☺\n☻\n☿\n〠\nヅ\nツ\n㋡\n웃\n유\nü\nÜ\nت\nシ\nッ\n㋛\nꑇ\nꐦ\nꐠ\nꐡ\nꐕ\nꌇ\nꌈ\nꉕ\nꈋ\nꈌ\nꆛ\nꆜ\nꃼ\n☠\n☃\n〲\n〴\nϡ\nﭢ\n⍢\n⍣\n⍤\n⍥\n⍨\n⍩\nὃ\nὕ\nὣ\nѶ\nӪ\nӫ\n⚣\n⚤\n⚥\n⚦\n⚧\n⚨\n⚢",
    "Punctuation Symbols": "·\n‑\n‒\n–\n—\n―\n‗\n‘\n’\n‚\n‛\n“\n”\n„\n‟\n•\n‣\n․\n‥\n…\n‧\n′\n″\n‴\n‵\n‶\n‷\n❛\n❜\n❝\n❞\nʹ\nʺ\nʻ\nʼ\nʽ\nʾ\nʿ\nˀ\nˁ\n˂\n˃\n˄\n˅\nˆ\nˇ\nˈ\nˉ\nˊ\nˋ\nˌ\nˍ\nˎ\nˏ\nː\nˑ\n˒\n˓\n˔\n˕\n˖\n˗\n˘\n˙\n˚\n˛\n˜\n˝\nˠ\nˡ\n～\n¿\n﹐\n﹒\n﹔\n﹕\n！\n＃\n＄\n％\n＆\n＊\n，\n．\n：\n；\n？\n＠\n、\n。\n〃\n〝\n〞\n︰",
    "Maths Symbols- Sum, Infinity, PI... Symbols": "π\n∞\nΣ\n√\n∛\n∜\n∫\n∬\n∭\n∮\n∯\n∰\n∱\n∲\n∳\n∀\n∁\n∂\n∃\n∄\n∅\n∆\n∇\n∈\n∉\n∊\n∋\n∌\n∍\n∎\n∏\n∐\n∑\n−\n∓\n∔\n∕\n∖\n∗\n∘\n∙\n∝\n∟\n∠\n∡\n∢\n∣\n∤\n∥\n∦\n∧\n∨\n∩\n∪\n∴\n∵\n∶\n∷\n∸\n∹\n∺\n∻\n∼\n∽\n∾\n∿\n≀\n≁\n≂\n≃\n≄\n≅\n≆\n≇\n≈\n≉\n≊\n≋\n≌\n≍\n≎\n≏\n≐\n≑\n≒\n≓\n≔\n≕\n≖\n≗\n≘\n≙\n≚\n≛\n≜\n≝\n≞\n≟\n≠\n≡\n≢\n≣\n≤\n≥\n≦\n≧\n≨\n≩\n≪\n≫\n≬\n≭\n≮\n≯\n≰\n≱\n≲\n≳\n≴\n≵\n≶\n≷\n≸\n≹\n≺\n≻\n≼\n≽\n≾\n≿\n⊀\n⊁\n⊂\n⊃\n⊄\n⊅\n⊆\n⊇\n⊈\n⊉\n⊊\n⊋\n⊌\n⊍\n⊎\n⊏\n⊐\n⊑\n⊒\n⊓\n⊔\n⊕\n⊖\n⊗\n⊘\n⊙\n⊚\n⊛\n⊜\n⊝\n⊞\n⊟\n⊠\n⊡\n⊢\n⊣\n⊤\n⊥\n⊦\n⊧\n⊨\n⊩\n⊪\n⊫\n⊬\n⊭\n⊮\n⊯\n⊰\n⊱\n⊲\n⊳\n⊴\n⊵\n⊶\n⊷\n⊸\n⊹\n⊺\n⊻\n⊼\n⊽\n⊾\n⊿\n⋀\n⋁\n⋂\n⋃\n⋄\n⋅\n⋆\n⋇\n⋈\n⋉\n⋊\n⋋\n⋌\n⋍\n⋎\n⋏\n⋐\n⋑\n⋒\n⋓\n⋔\n⋕\n⋖\n⋗\n⋘\n⋙\n⋚\n⋛\n⋜\n⋝\n⋞\n⋟\n⋠\n⋡\n⋢\n⋣\n⋤\n⋥\n⋦\n⋧\n⋨\n⋩\n⋪\n⋫\n⋬\n⋭\n⋮\n⋯\n⋰\n⋱\n⁺\n⁻\n⁼\n⁽\n⁾\nⁿ\n₊\n₋\n₌\n₍\n₎\n✖\n﹢\n﹣\n＋\n－\n／\n＝\n÷\n±\n×",
    "Number Symbols": "Ⅰ\nⅡ\nⅢ\nⅣ\nⅤ\nⅥ\nⅦ\nⅧ\nⅨ\nⅩ\nⅪ\nⅫ\nⅬ\nⅭ\nⅮ\nⅯ\nⅰ\nⅱ\nⅲ\nⅳ\nⅴ\nⅵ\nⅶ\nⅷ\nⅸ\nⅹ\nⅺ\nⅻ\nⅼ\nⅽ\nⅾ\nⅿ\nↀ\nↁ\nↂ\n➀\n➁\n➂\n➃\n➄\n➅\n➆\n➇\n➈\n➉\n➊\n➋\n➌\n➍\n➎\n➏\n➐\n➑\n➒\n➓\n⓵\n⓶\n⓷\n⓸\n⓹\n⓺\n⓻\n⓼\n⓽\n⓾\n⓿\n❶\n❷\n❸\n❹\n❺\n❻\n❼\n❽\n❾\n❿\n⁰\n¹\n²\n³\n⁴\n⁵\n⁶\n⁷\n⁸\n⁹\n₀\n₁\n₂\n₃\n₄\n₅\n₆\n₇\n₈\n₉\n⓪\n①\n②\n③\n④\n⑤\n⑥\n⑦\n⑧\n⑨\n⑩\n⑪\n⑫\n⑬\n⑭\n⑮\n⑯\n⑰\n⑱\n⑲\n⑳\n⑴\n⑵\n⑶\n⑷\n⑸\n⑹\n⑺\n⑻\n⑼\n⑽\n⑾\n⑿\n⒀\n⒁\n⒂\n⒃\n⒄\n⒅\n⒆\n⒇\n⒈\n⒉\n⒊\n⒋\n⒌\n⒍\n⒎\n⒏\n⒐\n⒑\n⒒\n⒓\n⒔\n⒕\n⒖\n⒗\n⒘\n⒙\n⒚\n⒛\n㈠\n㈡\n㈢\n㈣\n㈤\n㈥\n㈦\n㈧\n㈨\n㈩\n㊀\n㊁\n㊂\n㊃\n㊄\n㊅\n㊆\n㊇\n㊈\n㊉\n０\n１\n２\n３\n４\n５\n６\n７\n８\n９\nⁱ\nₐ\nₑ\nₒ\nₓ\nₔ",
    "Fraction Symbols": "⅟\n½\n⅓\n⅕\n⅙\n⅛\n⅔\n⅖\n⅚\n⅜\n¾\n⅗\n⅝\n⅞\n⅘\n¼\n⅐\n⅑\n⅒\n↉\n%\n℅\n‰\n‱",
    "Comparison Symbols": "≤\n≥\n≦\n≧\n≨\n≩\n⊰\n⊱\n⋛\n⋚\n≂\n≃\n≄\n≅\n≆\n≇\n≈\n≉\n≊\n≋\n≌\n≍\n≎\n≏\n≐\n≑\n≒\n≓\n≔\n≕\n≖\n≗\n≘\n≙\n≚\n≛\n≜\n≝\n≞\n≟\n≠\n≡\n≢\n≣",
    "Technical Symbols": "⌀\n⌂\n⌃\n⌄\n⌅\n⌆\n⌇\n⌈\n⌉\n⌊\n⌋\n⌌\n⌍\n⌎\n⌏\n⌐\n⌑\n⌒\n⌓\n⌔\n⌕\n⌖\n⌗\n⌘\n⌙\n⌚\n⌛\n⌜\n⌝\n⌞\n⌟\n⌠\n⌡\n⌢\n⌣\n⌤\n⌥\n⌦\n⌧\n⌨\n⌫\n⌬\n⌭\n⌮\n⌯\n⌰\n⌱\n⌲\n⌳\n⌴\n⌵\n⌶\n⌷\n⌸\n⌹\n⌺\n⌻\n⌼\n⌽\n⌾\n⌿\n⍀\n⍁\n⍂\n⍃\n⍄\n⍅\n⍆\n⍇\n⍈\n⍉\n⍊\n⍋\n⍌\n⍍\n⍎\n⍏\n⍐\n⍑\n⍒\n⍓\n⍔\n⍕\n⍖\n⍗\n⍘\n⍙\n⍚\n⍛\n⍜\n⍝\n⍞\n⍟\n⍠\n⍡\n⍢\n⍣\n⍤\n⍥\n⍦\n⍧\n⍨\n⍩\n⍪\n⍫\n⍬\n⍭\n⍮\n⍯\n⍰\n⍱\n⍲\n⍳\n⍴\n⍵\n⍶\n⍷\n⍸\n⍹\n⍺\n﹘\n﹝\n﹞\n﹟\n﹡\n〶\n␛\n␡\n␚\n␟\n␘\n␠\n␤\n␋\n␌\n␍\n␎\n␏\n␐\n␑\n␒\n␓\n␔\n␕\n␖\n␗\n␙\n␜\n␝\n␞\n␀\n␁\n␂\n␃\n␄\n␅\n␆\n␇\n␈\n␉\n␊\n␢\n␣\n⎋\n\nᴴᴰ",
    "Square & Rectangle Symbols": "❏\n❐\n❑\n❒\n▀\n▁\n▂\n▃\n▄\n▅\n▆\n▇\n▉\n▊\n▋\n█\n▌\n▐\n▍\n▎\n▏\n▕\n░\n▒\n▓\n▔\n▬\n▢\n▣\n▤\n▥\n▦\n▧\n▨\n▩\n▪\n▫\n▭\n▮\n▯\n☰\n☲\n☱\n☴\n☵\n☶\n☳\n☷\n▰\n▱\n◧\n◨\n◩\n◪\n◫\n∎\n■\n□\n⊞\n⊟\n⊠\n⊡\n❘\n❙\n❚\n〓\n◊\n◈\n◇\n◆\n⎔\n⎚\n☖\n☗",
    "Triangle Symbols": "◄\n▲\n▼\n►\n◀\n◣\n◥\n◤\n◢\n▶\n◂\n▴\n▾\n▸\n◁\n△\n▽\n▷\n∆\n∇\n⊳\n⊲\n⊴\n⊵\n◅\n▻\n▵\n▿\n◃\n▹\n◭\n◮\n⫷\n⫸\n⋖\n⋗\n⋪\n⋫\n⋬\n⋭\n⊿\n◬\n≜\n⑅",
    "Line Symbols": "│\n┃\n╽\n╿\n╏\n║\n╎\n┇\n︱\n┊\n︳\n┋\n┆\n╵\n〡\n〢\n╹\n╻\n╷\n〣\n☰\n☱\n☲\n☳\n☴\n☵\n☶\n☷\n≡\n✕\n═\n━\n─\n╍\n┅\n┉\n┄\n┈\n╌\n╴\n╶\n╸\n╺\n╼\n╾\n﹉\n﹍\n﹊\n﹎\n︲\n⑆\n⑇\n⑈\n⑉\n⑊\n⑄\n⑀\n︴\n﹏\n﹌\n﹋\n╳\n╲\n╱\n︶\n︵\n〵\n〴\n〳\n〆\n`\nᐟ\n‐\n⁃\n⎯\n〄",
    "Corner Symbols": "﹄\n﹃\n﹂\n﹁\n┕\n┓\n└\n┐\n┖\n┒\n┗\n┑\n┍\n┙\n┏\n┛\n┎\n┚\n┌\n┘\n「\n」\n『\n』\n˩\n˥\n├\n┝\n┞\n┟\n┠\n┡\n┢\n┣\n┤\n┥\n┦\n┧\n┨\n┩\n┪\n┫\n┬\n┭\n┮\n┯\n┰\n┱\n┲\n┳\n┴\n┵\n┶\n┷\n┸\n┹\n┺\n┻\n┼\n┽\n┾\n┿\n╀\n╁\n╂\n╃\n╄\n╅\n╆\n╇\n╈\n╉\n╊\n╋\n╒\n╕\n╓\n╖\n╔\n╗\n╘\n╛\n╙\n╜\n╚\n╝\n╞\n╡\n╟\n╢\n╠\n╣\n╥\n╨\n╧\n╤\n╦\n╩\n╪\n╫\n╬\n〒\n⊢\n⊣\n⊤\n⊥\n╭\n╮\n╯\n╰\n⊦\n⊧\n⊨\n⊩\n⊪\n⊫\n⊬\n⊭\n⊮\n⊯\n⊺\n〦\n〧\n〨\n˦\n˧\n˨\n⑁\n⑂\n⑃\n∟",
    "Circle Symbols": "◉\n○\n◌\n◍\n◎\n●\n◐\n◑\n◒\n◓\n◔\n◕\n◖\n◗\n❂\n☢\n⊗\n⊙\n◘\n◙\n◚\n◛\n◜\n◝\n◞\n◟\n◠\n◡\n◯\n〇\n〶\n⚫\n⬤\n◦\n∅\n∘\n⊕\n⊖\n⊘\n⊚\n⊛\n⊜\n⊝\n❍\n⦿",
    "Phonetic Symbols": "ʌ\nɑ:\næ\ne\nə\nɜ:\nɪ\ni:\nɒ\nɔ:\nʊ\nu:\naɪ\naʊ\neɪ\noʊ\nɔɪ\neə\nɪə\nʊə\nb\nd\nf\ng\nh\nj\nk\nl\nm\nn\nŋ\np\nr\ns\nʃ\nt\ntʃ\nθ\nð\nv\nw\nz\nʒ\ndʒ",
    "Latin Letters Symbols": "ą\nč\nĤ\nħ\nĩ\nŇ\nŘ\nŤ\nŴ\nŽ\nⒶ\nⒷ\nⒸ\nⒹ\nⒺ\nⒻ\nⒼ\nⒽ\nⒾ\nⒿ\nⓀ\nⓁ\nⓂ\nⓃ\nⓄ\nⓅ\nⓆ\nⓇ\nⓈ\nⓉ\nⓊ\nⓋ\nⓌ\nⓍ\nⓎ\nⓏ\nⓐ\nⓑ\nⓒ\nⓓ\nⓔ\nⓕ\nⓖ\nⓗ\nⓘ\nⓙ\nⓚ\nⓛ\nⓜ\nⓝ\nⓞ\nⓟ\nⓠ\nⓡ\nⓢ\nⓣ\nⓤ\nⓥ\nⓦ\nⓧ\nⓨ\nⓩ\n\nSee more Latin Letters Symbols",
    "Greek Letters Symbols": "α\nβ\nγ\nδ\nε\nζ\nη\nθ\nι\nκ\nλ\nμ\nν\nξ\nο\nπ\nρ\nς\nσ\nτ\nυ\nφ\nχ\nψ\nω\nΑ\nΒ\nΓ\nΔ\nΕ\nΖ\nΗ\nΘ\nΙ\nΚ\nΛ\nΜ\nΝ\nΞ\nΟ\nΠ\nΡ\nΣ\nΤ\nΥ\nΦ\nΧ\nΨ\nΩ",
    "Chinese Symbols": "㊊\n㊋\n㊌\n㊍\n㊎\n㊏\n㊐\n㊑\n㊒\n㊓\n㊔\n㊕\n㊖\n㊗\n㊘\n㊙\n㊚\n㊛\n㊜\n㊝\n㊞\n㊟\n㊠\n㊡\n㊢\n㊣\n㊤\n㊥\n㊦\n㊧\n㊨\n㊩\n㊪\n㊫\n㊬\n㊭\n㊮\n㊯\n㊰",
    "Japanese Symbols": "ぁ\nあ\nぃ\nい\nぅ\nう\nぇ\nえ\nぉ\nお\nか\nが\nき\nぎ\nく\nぐ\nけ\nげ\nこ\nご\nさ\nざ\nし\nじ\nす\nず\nせ\nぜ\nそ\nぞ\nた\nだ\nち\nぢ\nっ\nつ\nづ\nて\nで\nと\nど\nな\nに\nぬ\nね\nの\nは\nば\nぱ\nひ\nび\nぴ\nふ\nぶ\nぷ\nへ\nべ\nぺ\nほ\nぼ\nぽ\nま\nみ\n\nSee more Japanese Letters Symbols",
    "Korean Symbols": "ㄱ\nㄲ\nㄳ\nㄴ\nㄵ\nㄶ\nㄷ\nㄸ\nㄹ\nㄺ\nㄻ\nㄼ\nㄽ\nㄾ\nㄿ\nㅀ\nㅁ\nㅂ\nㅃ\nㅄ\nㅅ\nㅆ\nㅇ\nㅈ\nㅉ\nㅊ\nㅋ\nㅌ\nㅍ\nㅎ\nㅏ\nㅐ\nㅑ\nㅒ\nㅓ\nㅔ\nㅕ\nㅖ\nㅗ\nㅘ\nㅙ\nㅚ\nㅛ\nㅜ\nㅝ\nㅞ\nㅟ\nㅠ\nㅡ\nㅢ\nㅥ\nㅦ\nㅧ\nㅨ\nㅩ\nㅪ\nㅫ\nㅬ\nㅭ\nㅮ\nㅯ\nㅰ\nㅱ\nㅲ\nㅳ\nㅴ\nㅵ\nㅶ\nㅷ\nㅸ\nㅹ\nㅺ\nㅻ\nㅼ\nㅽ\nㅾ\nㅿ\nㆀ\nㆁ\nㆂ\nㆃ\nㆄ\nㆅ\nㆆ\nㆇ\nㆈ\nㆉ\nㆊ",
    "Smileys & Emotion Emoji Symbols": "😂\n😄\n😃\n😀\n😊\n😉\n😍\n😘\n😚\n😗\n😙\n😜\n😝\n😛\n😳\n😁\n😔\n😌\n😒\n😞\n😣\n😢\n😭\n😪\n😥\n😰\n😅\n😓\n😩\n😫\n😨\n😱\n😠\n😡\n😤\n😖\n😆\n😋\n😷\n😎\n😴\n😵\n😲\n😟\n😦\n😧\n😈\n👿\n😮\n😬\n😐\n😕\n😯\n😶\n😇\n☺️\n😏\n😑\n🙃\n🙄\n☹️\n🤐\n🤑\n🤒\n🤓\n🤔\n🤕\n🙁\n🙂\n🤗\n🤣\n🤠\n🤥\n🤤\n🤢\n🤧\n🤡\n🤖\n🖤\n💛\n💙\n💜\n💚\n🧡\n❤️️\n💔\n💗\n💓\n💕\n💖\n💞\n💘\n💝\n❣️\n💌\n💋\n😺\n😸\n😻\n😽\n😼\n🙀\n😿\n😹\n😾\n🙈\n🙉\n🙊\n💀\n👽\n👹\n👺\n🤩\n🤨\n🥺️\n🤯\n🤪\n🤬\n🤮\n🤫\n🤭\n🧐\n🥰️\n🥵️\n🥶️\n🥴️\n🥳️\n🥲\n🥸",
    "People & Body Emoji Symbols": "👶\n👦\n👧\n👨\n👩\n👼\n🤰\n🤳\n👸\n🤴\n🧔\n🕺\n💃\n🥷\n🕴️\n👻\n🎎\n☃️\n☠️\n👁‍🗨\n🗿\n👲\n👂\n👀\n👃\n👅\n👄\n👁\n🫁\n🫀\n👤\n👥\n🗣\n🫂\n💬\n💭\n🗨\n🗯\n🧒\n🧑\n🧕\n🤱\n🦵️\n🦶️\n🦷️\n🦴️\n👪\n👨‍👦\n👨‍👦‍👦\n👨‍👧\n👨‍👧‍👦\n👨‍👧‍👧\n👨‍👩‍👦\n👩‍👦\n👩‍👦‍👦\n👩‍👧\n👩‍👧‍👦\n👩‍👧‍👧\n👨‍👨‍👦\n👨‍👨‍👦‍👦\n👨‍👨‍👧\n👨‍👨‍👧‍👦\n👨‍👨‍👧‍👧\n👨‍👩‍👦‍👦\n👨‍👩‍👧\n👨‍👩‍👧‍👦\n👨‍👩‍👧‍👧\n👩‍👩‍👦\n👩‍👩‍👦‍👦\n👩‍👩‍👧\n👩‍👩‍👧‍👦\n👩‍👩‍👧‍👧\n💏\n👩‍❤️‍💋‍👨\n👨‍❤️‍💋‍👨\n👩‍❤️‍💋‍👩\n💑\n👩‍❤️‍👨\n👨‍❤️‍👨\n👩‍❤️‍👩\n🤵\n🤵‍♂️\n🤵‍♀️\n🧑‍🦳\n👨‍🦳️\n👩‍🦳️\n🧑‍🦱\n👨‍🦱️\n👩‍🦱️\n🧑‍🦲\n👨‍🦲️\n👩‍🦲️\n🧓\n👴\n👵\n🧑‍🦰\n👨‍🦰️\n👩‍🦰️\n👱\n👱‍♂️\n👱‍♀️\n👰\n👰‍♂️\n👰‍♀️\n🧑‍🎄\n🎅\n🎅\n🙆\n🙆‍♂️\n🙆‍♀️\n🙅\n🙅‍♂️\n🙅‍♀️\n💁\n💁‍♂️\n💁‍♀️\n🙋\n🙋‍♂️\n🙋‍♀️\n🤷\n🤷‍♂️\n🤷‍♀️\n🙍\n🙍‍♂️\n🙍‍♀️\n💆\n💆‍♂️\n💆‍♀️\n💇\n💇‍♂️\n💇‍♀️\n🙎\n🙎‍♂️\n🙎‍♀️\n🤦\n🤦‍♂️\n🤦‍♀️\n👮\n👮‍♂️\n👮‍♀️\n👷\n👷‍♂️\n👷‍♀️\n🧏\n🧏‍♂️\n🧏‍♀️\n💂\n💂‍♂️\n💂‍♀️\n🕵\n🕵️‍♂️\n🕵️‍♀️\n🙇\n🙇‍♂️\n🙇‍♀️\n🚶\n🚶‍♂️\n🚶‍♀️\n🏃\n🏃‍♂️\n🏃‍♀️\n🧙\n🧙‍♂️\n🧙‍♀️\n🧚\n🧚‍♂️\n🧚‍♀️\n🧛\n🧛‍♂️\n🧛‍♀️\n🧜\n🧜‍♂️\n🧜‍♀️\n🧝\n🧝‍♂️\n🧝‍♀️\n🧞\n🧞‍♂️\n🧞‍♀️\n🧖\n🧖‍♂️\n🧖‍♀️\n👳\n👳‍♀️\n👳‍♀️\n🧗\n🧗‍♂️\n🧗‍♀️\n🧘\n🧘‍♂️\n🧘‍♀️\n🧟\n🧟‍♂️\n🧟‍♀️\n🦸️\n🦸‍♂️️\n🦸‍♀️️\n🦹️\n🦹‍♂️️\n🦹‍♀️️\n👯\n👯‍♂️\n👯\n🚵\n🚵‍♂️\n🚵‍♀️\n🚴\n🚴‍♂️\n🚴‍♀️\n⛹\n⛹️‍♂️\n⛹️‍♀️\n🏊\n🏊‍♂️\n🏊‍♀️\n🏄\n🏄‍♂️\n🏄‍♀️\n🤹\n🤹‍♂️\n🤹‍♀️\n🏋\n🏋️‍♂️\n🏋️‍♀️\n🏌\n🏌️‍♂️\n🏌️‍♀️\n🤸\n🤸‍♂️\n🤸‍♀️\n🚣\n🚣‍♂️\n🚣‍♀️\n🤽\n🤽‍♂️\n🤽‍♀️\n🤾\n🤾‍♂️\n🤾‍♀️\n🧑‍🍼\n👨‍🍼\n👩‍🍼\n🧑‍🎓\n👨‍🎓\n👩‍🎓\n🧑‍🎤\n👨‍🎤\n👩‍🎤\n🧑‍🍳\n👨‍🍳\n👩‍🍳\n🧑‍🚒\n👨‍🚒\n👩‍🚒\n🧑‍🤝‍🧑\n👫\n👬\n👭\n🧑‍🦽\n👨‍🦽\n👩‍🦽\n👨‍🦼\n👩‍🦼\n🧑‍🦼\n🧑‍🎨\n👨‍🎨\n👩‍🎨\n🧑‍🦯\n👨‍🦯\n👩‍🦯\n🧑‍🚀\n👨‍🚀\n👩‍🚀\n🧑‍🌾\n👨‍🌾\n👩‍🌾\n🧑‍⚖️\n👨‍⚖️\n👩‍⚖️\n🧑‍🔧\n👨‍🔧\n👩‍🔧\n🧑‍💼\n👨‍💼\n👩‍💼\n🧑‍⚕️\n👨‍⚕️\n👩‍⚕️\n🧑‍💻\n👨‍💻\n👩‍💻\n🧑‍🔬\n👨‍🔬\n👩‍🔬\n🧑‍🏫\n👨‍🏫\n👩‍🏫\n🧑‍🏭\n👨‍🏭\n👩‍🏭\n🧑‍✈️\n👨‍✈️\n👩‍✈️",
    "Objects Emoji Symbols": "🎍\n🎒\n🎓\n🎏\n🎆\n🎇\n🎐\n🎑\n🎃\n🎄\n🎁\n🎋\n🎉\n🎊\n🎈\n🎌\n🔮\n🎥\n📷\n📹\n📼\n💿\n📀\n💽\n💾\n💻\n📱\n☎️\n📞\n📟\n🛰\n📠\n📡\n📺\n📻\n🔊\n🔉\n🔈\n🔇\n🔔\n🔕\n📢\n📣\n⏳\n⌛️\n⏰\n⌚️\n🔓\n🔒\n🔏\n🔐\n🔑\n🔎\n💡\n🔦\n🔆\n🔅\n🔌\n🔋\n🔍\n🛁\n🛀\n🚿\n🚽\n🔧\n🔩\n🔨\n🚪\n🚬\n💣\n🔫\n🔪\n💊\n💉\n💰\n💴\n💵\n💷\n💶\n💳\n💸\n📲\n📧\n📥\n📤\n✉️\n📩\n📨\n📯\n📫\n📪\n📬\n📭\n📮\n📦\n📝\n📄\n📃\n📑\n📊\n📈\n📉\n📜\n📋\n📅\n📆\n📇\n📁\n📂\n✂️\n📌\n📎\n✒️\n✏️\n📏\n📐\n📕\n📗\n📘\n📙\n📓\n📔\n📒\n📚\n📖\n🔖\n📛\n🔬\n🔭\n📰\n🎨\n🎬\n🎤\n🎧\n🎼\n🎵\n🎶\n🎹\n🎻\n🎺\n🎷\n🎸\n👾\n🎮\n🃏\n🎴\n️🀄️\n🏺\n📿\n🕋\n⚒️\n⚔️\n⚖️\n⚗️\n⚙️\n⌨️\n🕶\n⏱\n⏲\n☂️\n⚜️\n⚰️\n⚱️\n⛏\n⛑\n⛓\n⛩\n⛱\n🎰\n🎩\n👑\n👒\n💼\n👜\n👝\n👛\n👓\n🎀\n🌂\n💄\n💍\n💎\n👣\n🌡\n🎖\n🎗\n🎙\n🎚\n🎛\n🎞\n🎟\n🏅\n🏔\n🏕\n🏖\n🏵\n🏷\n📸\n📽\n🕉\n🕊\n🕯\n🕰\n🕳\n🕸\n🕹\n💩\n🖇\n🖊\n🖋\n🖌\n🖍\n🖥\n🖨\n🖱\n🖲\n🖼\n🗂\n🗃\n🗄\n🗑\n🗒\n🗓\n🗜\n🗝\n🗞\n🗡\n🗳\n🗺\n🛋\n🛌\n🛍\n🛎\n🛏\n🛠\n🛡\n🛢\n👟\n👞\n👡\n👠\n👢\n👕\n👔\n👚\n👗\n🎽\n👖\n👘\n👙\n🏮\n🎪\n🎭\n📍\n⛽️\n🥂\n🥃\n🥄\n🥁\n🛒\n🧠\n🧣\n🧤\n🧥\n🧦\n🧢\n🧭️\n🧱️\n🧳️\n🧨️\n🧧️\n🥎️\n🥏️\n🥍️\n🧿️\n🧩️\n🧸️\n♟️\n🧵\n🧶\n🥽\n🥼\n🥾\n🥿️\n🧮️\n🧾️\n🧰️️\n🧲️️\n🧪️️\n🧫️️\n🧬️️\n🧴️️\n🧷️️\n🧹️️\n🧺️️\n🧻️️\n🧼️️\n🧽️️\n🧯️️\n💈\n🍼\n🛼\n🫖\n🪄\n🪖\n🪞\n🪤\n🪆\n🪢\n🪜\n🪘\n🪝\n🪟\n🩴\n🪥\n🪛\n🪅\n🪧\n🪠\n🪡\n🪶\n🪃\n🪣\n🪗\n🪚\n🪙",
    "Nature Emoji Symbols": "💐\n🌸\n🌷\n🍀\n🌹\n🥀\n🌻\n🌺\n🍁\n🍃\n🍂\n🌿\n🌾\n🍄\n🌵\n🌴\n🌲\n🌳\n🌰\n🌱\n🌼\n🌐\n🌞\n🌝\n🌚\n🌑\n🌒\n🌓\n🌓\n🌔\n🌕\n🌖\n🌗\n🌘\n🌜\n🌛\n🌙\n🔥\n💧",
    "Symbols Emoji": "♾️\n♀️\n♂️\n⚧️\n⚕️\n➰\n➿\n💲\n💱\n©️\n®️\n™️\n〰️\n🔠\n🔡\n🔤\nℹ️\n🆗\n🆕\n🆙\n🆒\n🆓\n🆖\n📶\n🎦\n🚻\n🚹\n🚺\n🚼\n🚾\n🚮\n🅿️\n♿️\nⓂ️\n🛂\n🛄\n🛅\n🛃\n🆑\n🆘\n🆚\n🚫\n🚭\n🔞\n📵\n🚯\n🚱\n🚳\n🚷\n🚸\n⛔️\n⚠️\n🛑\n🚧\n✳️\n❇️\n❎\n✅\n✴️\n💟\n📳\n📴\n🅰️\n🅱️\n🆎\n🅾️\n💠\n♻️\n🏧\n🚰\n💹\n〽️\n❌\n⭕️\n❗️\n❓\n❕\n❔\n🕛\n🕧\n🕐\n🕜\n🕑\n🕝\n🕒\n🕞\n🕓\n🕟\n🕔\n🕠\n🕕\n🕖\n🕗\n🕘\n🕙\n🕚\n🕡\n🕢\n🕣\n🕤\n🕥\n🕦\n1⃣\n2⃣\n3⃣\n4⃣\n5⃣\n6⃣\n7⃣\n8⃣\n9⃣\n0⃣\n🔟\n🔢\n#️⃣\n🔣\n⏭\n⏮\n⏯\n*️⃣\n⏸\n⏹\n⏺\n⏏️\n☢️\n☣️\n➕\n➖\n✖️\n➗\n♥️\n♦️\n♣️\n♠️\n💮\n💯\n💫\n💥\n💢\n💦\n💤\n💨\n✔️\n☑️\n🔘\n🔗\n🔱\n🔲\n🔳\n⬜️\n⬛️\n◼️\n◻️\n◾️\n◽️\n▪️\n▫️\n🔺\n⚫️\n⚪️\n🔴\n🔵\n🔻\n🔶\n🔷\n🔸\n🔹\n⁉️\n‼️\n🔰\n🆔\n*️⃣\n🛗\n☮️\n🛐\n🕎\n✝️\n✡️\n☦️\n☪️\n☯️\n☸️\n⚛️\n♈️\n♉️\n♊️\n♋️\n♌️\n♍️\n♎️\n♏️\n♐️\n♑️\n♒️\n♓️\n⛎\n🔯\n🇦\n🇧\n🇨\n🇩\n🇪\n🇫\n🇬\n🇭\n🇮\n🇯\n🇰\n🇱\n🇲\n🇳\n🇴\n🇵\n🇶\n🇷\n🇸\n🇹\n🇺\n🇻\n🇼\n🇽\n🇾\n🇿\n🈁\n🈯️\n🈳\n🈵\n🈴\n🈲\n🉐\n🈹\n🈺\n🈶\n🈚️\n🈷️\n🈸\n🈂️\n🉑\n㊙️\n㊗️",
    "Food & Drink Emoji Symbols": "☕️\n🍵\n🍶\n🍺\n🍻\n🍸\n🍹\n🍷\n🍴\n🍕\n🍔\n🍟\n🍗\n🍖\n🍝\n🍛\n🍤\n🍱\n🍣\n🍥\n🍙\n🍘\n🍚\n🍜\n🍲\n🍢\n🍡\n🍳\n🍞\n🍩\n🍮\n🍦\n🍨\n🍧\n🎂\n🍰\n🍪\n🍫\n🍬\n🍭\n🍯\n🍎\n🍏\n🍊\n🍋\n🍒\n🍇\n🍉\n🍓\n🍑\n🍈\n🍌\n🍐\n🍍\n🍠\n🍆\n🍅\n🌽\n🌶\n🌭\n🌮\n🌯\n🍾\n🍿\n🥝\n🥑\n🥔\n🥕\n🥒\n🥜\n🥐\n🥖\n🥞\n🥓\n🥙\n🥚\n🥘\n🥗\n🥛\n🥥\n🥦\n🥨\n🥩\n🥪\n🥣\n🥫\n🥟\n🥠\n🥡\n🥧\n🥤\n🥢\n🥭️\n🥬️\n🥯️\n🧂️\n🥮️\n🦞️\n🧁️\n🫕\n🫒\n🫓\n🫔\n🫑\n🫐\n🧋",
    "Transportation Emoji Symbols": "🚢\n⛵️\n🚤\n⚓️\n🚀\n✈️\n💺\n🚁\n🚂\n🚊\n🚉\n🚞\n🚆\n🚄\n🚅\n🚈\n🚇\n🚝\n🚋\n🚃\n🚎\n🚌\n🚍\n🚙\n🚘\n🚗\n🚕\n🚖\n🚛\n🚚\n🚨\n🚓\n🚔\n🚒\n🚑\n🚐\n🚲\n🚡\n🚟\n🚠\n⛴\n🚜\n🚏\n🛣\n🛤\n🛥\n🛩\n🛫\n🛬\n🛳\n🎫\n🚦\n🚥\n🎠\n🎡\n🎢\n🛴\n🛹️\n🛵\n🛶\n🛷\n🛸\n🛻",
    "Animals Emoji Symbols": "🐶\n🐺\n🐱\n🐭\n🐹\n🐰\n🐸\n🐯\n🐨\n🐻\n🐷\n🐽\n🐮\n🐗\n🐵\n🐒\n🐴\n🐑\n🐘\n🐼\n🐧\n🐦\n🐤\n🐥\n🐣\n🐔\n🐍\n🐢\n🐛\n🐝\n🐜\n🐿\n🐞\n🐌\n🐙\n🐚\n🐠\n🐟\n🐬\n🐳\n🐋\n🐄\n🐏\n🐀\n🐃\n🐅\n🐇\n🐉\n🐎\n🐐\n🐓\n🐕\n🐖\n🐁\n🐂\n🐲\n🐡\n🐊\n🐫\n🐪\n🐆\n🐈\n🐩\n🐾\n🦀\n🦁\n🦂\n🕷\n🦃\n🦄\n🦐\n🦑\n🦋\n🦍\n🦊\n🦌\n🦏\n🦇\n🦅\n🦆\n🦉\n🦎\n🦈\n🦓\n🦒\n🦔\n🦕\n🦖\n🦝️\n🦙️\n🦛️\n🦘️\n🦡️\n🦢️\n🦚️\n🦜️\n🦟️\n🐻‍❄️\n🦭\n🐃\n🪱\n🦬\n🪳\n🦣\n🦤\n🐈‍⬛\n🦗\n🦫\n🪲\n🪰",
    "Hands Emoji Symbols": "👍\n👎\n👌\n👊\n✊\n✌️\n👋\n✋\n👐\n👆\n👇\n👉\n👈\n🙌\n🙏\n💪\n🖖\n🖐\n☝️\n👏\n✍️\n🤘\n🖕\n🤞\n🤙\n🤛\n🤜\n🤚\n🤝\n🤟\n🤲\n🤌\n💅",
    "Arrows Emoji Symbols": "⬆️\n⬇️\n⬅️\n➡️\n↗️\n↖️\n↘️\n↙️\n↔️\n↕️\n🔄\n◀️\n▶️\n🔼\n🔽\n↩️\n↪️\n⏪\n⏩\n⏫\n⏬\n⤵️\n⤴️\n🔀\n🔁\n🔂\n🔃\n🔝\n🔚\n🔙\n🔛\n🔜",
    "Buildings Emoji Symbols": "🏠\n🏡\n🏫\n🏢\n🏣\n🏥\n🏦\n🏪\n🏩\n🏨\n💒\n⛪️\n🏬\n🏤\n🌇\n🕌\n🕍\n🌆\n🏯\n🏰\n⛺️\n🏭\n🗼\n🏘\n🏞\n🏟\n🏙\n🏚\n🏛\n🏗\n🛖\n🪦",
    "Sport Emoji Symbols": "🎲\n🎯\n🏈\n🏀\n️⚽️\n⚾️\n🎾\n🎱\n🏉\n🎳\n️⛳️\n🏁\n🏇\n🏆\n⛷\n⛸\n🏏\n🏐\n🏑\n🏒\n🏓\n🏸\n🏹\n🏂\n🏍\n🏎\n🤺\n🥅\n🥇\n🥈\n🥉\n🥊\n🥋\n🤼\n🤼‍♂️\n🎣\n🥌",
    "Flags Emoji Symbols": "🇯🇵\n🇰🇷\n🇩🇪\n🇨🇳\n🇺🇸\n🇫🇷\n🇪🇸\n🇮🇹\n🇷🇺\n🇬🇧\n🇦🇿\n🇦🇺\n🇦🇼\n🇦🇴\n🇦🇱\n🇦🇲\n🇦🇸\n🇦🇹\n🇦🇪\n🇦🇬\n🇦🇫\n🇦🇮\n🇦🇩\n🇦🇷\n🇧🇴\n🇧🇷\n🇧🇳\n🇧🇲\n🇧🇹\n🇧🇸\n🇧🇾\n🇧🇿\n🇧🇼\n🇧🇪\n🇧🇫\n🇧🇬\n🇧🇭\n🇧🇮\n🇧🇯\n🇧🇦\n🇧🇧\n🇧🇩\n🇨🇻\n🇨🇼\n🇨🇺\n🇨🇿\n🇨🇾\n🇨🇲\n🇨🇰\n🇨🇱\n🇨🇷\n🇨🇴\n🇨🇩\n🇨🇦\n🇨🇬\n🇨🇫\n🇨🇮\n🇨🇭\n🇩🇯\n🇩🇲\n🇩🇰\n🇩🇴\n🇩🇿\n🇪🇹\n🇪🇷\n🇪🇬\n🇪🇪\n🇪🇨\n🇫🇴\n🇫🇮\n🇫🇯\n🇬🇹\n🇬🇳\n🇬🇲\n🇬🇵\n🇬🇷\n🇬🇶\n🇬🇺\n🇬🇼\n🇬🇾\n🇬🇫\n🇬🇭\n🇬🇮\n🇬🇪\n🇬🇩\n🇬🇦\n🇭🇺\n🇭🇷\n🇭🇳\n🇭🇰\n🇭🇹\n🇮🇪\n🇮🇩\n🇮🇷\n🇮🇶\n🇮🇳\n🇮🇱\n🇮🇸\n🇯🇴\n🇯🇲\n🇰🇬\n🇰🇪\n🇰🇭\n🇰🇮\n🇰🇼\n🇰🇿\n🇰🇾\n🇰🇳\n🇰🇲\n🇰🇵\n🇱🇰\n🇱🇷\n🇱🇸\n🇱🇹\n🇱🇻\n🇱🇺\n🇱🇾\n🇱🇮\n🇱🇨\n🇱🇧\n🇱🇦\n🇲🇼\n🇲🇻\n🇲🇴\n🇲🇪\n🇲🇬\n🇲🇩\n🇲🇦\n🇲🇳\n🇲🇲\n🇲🇷\n🇲🇶\n🇲🇹\n🇲🇸\n🇲🇾\n🇲🇽\n🇲🇿\n🇲🇱\n🇲🇰\n🇲🇵\n🇳🇮\n🇳🇦\n🇳🇱\n🇳🇴\n🇳🇵\n🇳🇿\n🇳🇺\n🇳🇪\n🇳🇨\n🇳🇬\n🇴🇲\n🇵🇸\n🇵🇰\n🇵🇾\n🇵🇼\n🇵🇭\n🇵🇬\n🇵🇪\n🇵🇦\n🇵🇷\n🇵🇹\n🇵🇱\n🇶🇦\n🇷🇪\n🇷🇸\n🇷🇴\n🇷🇼\n🇸🇲\n🇸🇦\n🇸🇧\n🇸🇨\n🇸🇩\n🇸🇬\n🇸🇪\n🇸🇮\n🇸🇻\n🇸🇿\n🇸🇾\n🇸🇽\n🇸🇹\n🇸🇸\n🇸🇳\n🇸🇱\n🇸🇰\n🇸🇷\n🇸🇴\n🇹🇴\n🇹🇿\n🇹🇹\n🇹🇲\n🇹🇳\n🇹🇱\n🇹🇷\n🇹🇻\n🇹🇬\n🇹🇫\n🇹🇯\n🇹🇭\n🇹🇨\n🇺🇿\n🇺🇾\n🇺🇬\n🇺🇦\n🇻🇺\n🇻🇳\n🇻🇨\n🇻🇪\n🇻🇬\n🇻🇮\n🇼🇸\n🇾🇪\n🇿🇦\n🇿🇼\n🇿🇲\n🇦🇶\n🇦🇽\n🇧🇱\n🇧🇶\n🇨🇨\n🇨🇽\n🇪🇭\n🇪🇺\n🇫🇰\n🇫🇲\n🇬🇬\n🇬🇱\n🇬🇸\n🇮🇨\n🇮🇲\n🇮🇴\n🇯🇪\n🇲🇨\n🇲🇭\n🇲🇺\n🇳🇫\n🇳🇷\n🇵🇫\n🇵🇲\n🇵🇳\n🇸🇭\n🇹🇩\n🇹🇰\n🇹🇼\n🇻🇦\n🇼🇫\n🇽🇰\n🇾🇹\n🇦🇨\n🇧🇻\n🇪🇦\n🇨🇵\n🇩🇬\n🇭🇲\n🇲🇫\n🇸🇯\n🇹🇦\n🇺🇲\n🏴󠁧󠁢󠁥󠁮󠁧󠁿\n🏴󠁧󠁢󠁳󠁣󠁴󠁿\n🏴󠁧󠁢󠁷󠁬󠁳󠁿\n🇺🇳\n🚩\n🏳\n🏴\n🏳️‍🌈\n🏴‍☠️️\n🏳️‍⚧️"
}


num_columns = 8
page_size = 5

@bot.on_callback_query(filters.regex(r'^syback:\d+:\d+') | filters.regex(r'^synext:\d+:\d+'))
async def sym_next_back(_, query):
    user_id = int(query.data.split(':')[1])
    target_index = int(query.data.split(':')[2])

    if query.from_user.id != user_id:
        return await query.answer(font('Sorry this is not your Query.'))

    # Calculate the start index of the current page
    if query.data.startswith('syback'):
        target_index = max(0, target_index - page_size)
    else:
        target_index = min(len(data) - page_size, target_index + page_size)

    buttons = []
    for index, (title, content) in enumerate(data.items()):
        if index < target_index:
            continue
        if index >= target_index + page_size:
            break
        buttons.append(
            types.InlineKeyboardButton(
                title, callback_data=f'symbol:{user_id}:{index}', style=enums.ButtonStyle.PRIMARY
            )
        )

    columns_btn = [[button] for button in buttons]
    
    # Add navigation buttons
    navigation_buttons = []
    if target_index > 0:
        navigation_buttons.append(
            types.InlineKeyboardButton(
                "⬅️ Back", callback_data=f'syback:{user_id}:{target_index}', style=enums.ButtonStyle.SUCCESS
            )
        )
    if target_index + page_size < len(data):
        navigation_buttons.append(
            types.InlineKeyboardButton(
                "Next ➡️", callback_data=f'synext:{user_id}:{target_index}', style=enums.ButtonStyle.SUCCESS
            )
        )

    if navigation_buttons:
        columns_btn.append(navigation_buttons)

    reply_markup = types.InlineKeyboardMarkup(columns_btn)

    await query.message.edit_text(
        "**Here are some symbols for you to explore. I hope you find something special today!**",
        reply_markup=reply_markup
    )

@bot.on_message(filters.command("symbols") & ~filters.forwarded, group=-543)
async def symbols(_, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    buttons = []
    for index, (title, content) in enumerate(data.items()):
        if index >= page_size:
            break
        buttons.append(
            types.InlineKeyboardButton(
                title, callback_data=f'symbol:{user_id}:{index}', style=enums.ButtonStyle.PRIMARY
            )
        )

    columns_btn = [[button] for button in buttons]
    
    # Add navigation buttons if there are more pages
    navigation_buttons = []
    if page_size < len(data):
        navigation_buttons.append(
            types.InlineKeyboardButton(
                "Next ➡️", callback_data=f'synext:{user_id}:{0}', style=enums.ButtonStyle.SUCCESS
            )
        )
    if navigation_buttons:
        columns_btn.append(navigation_buttons)

    reply_markup = types.InlineKeyboardMarkup(columns_btn)

    await bot.send_message(
        chat_id=chat_id,
        text="**Here are some symbols for you to explore. I hope you find something special today!**",
        reply_markup=reply_markup
    )
    

@bot.on_callback_query(filters.regex('^symbol'))
async def cb_symbols(_, query):
    user_id = int(query.data.split(':')[1])
    target_index = int(query.data.split(':')[2])
    if query.from_user.id != user_id:
        return await query.answer(
            'Sorry, this is not your Query.', show_alert=True)

    text = ''

    for index, (title, content) in enumerate(data.items()):
        if index == target_index:
            text += f'**{title}**:\n\n'
            symbols = content.split()
            for i in range(0, len(symbols), num_columns):
                row = symbols[i:i + num_columns]
                formatted_row = '  '.join(f'`{symbol}`' for symbol in row)
                text += f'{formatted_row}\n'
            break

    return await query.message.edit_text(
         text=text,
    reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton(
        text='Back ⬅️', callback_data=f'syback:{user_id}:{target_index}', style=enums.ButtonStyle.SUCCESS
    )]])
    )
