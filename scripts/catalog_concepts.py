#!/usr/bin/env python3
"""Cem conceitos de produção a partir do #122 (modo ambient)."""

from __future__ import annotations

from typing import NamedTuple


class CatalogConcept(NamedTuple):
    number: str
    series: str
    title: str
    hours: int
    mood: str
    rain_volume: float
    cafe_volume: float
    no_rain: bool
    no_cafe: bool
    keywords: tuple[str, ...]
    visual: str


def _row(
    number: int,
    series: str,
    title: str,
    hours: int,
    mood: str,
    rain: float,
    cafe: float,
    no_rain: bool,
    no_cafe: bool,
    keywords: str,
    visual: str,
) -> CatalogConcept:
    return CatalogConcept(
        number=f"{number:03d}",
        series=series,
        title=title,
        hours=hours,
        mood=mood,
        rain_volume=rain,
        cafe_volume=cafe,
        no_rain=no_rain,
        no_cafe=no_cafe,
        keywords=tuple(part for part in keywords.split() if part),
        visual=visual,
    )


CONCEPTS: tuple[CatalogConcept, ...] = (
    _row(122, "Ambience Session", "Porto Ribeira Cafe", 8, "Porto Ribeira • Warm Focus", 0.06, 0.08, False, False, "cafe amber golden afternoon", "cozy riverside cafe in Porto at dusk, tiled walls, warm pendant lamps, laptop on a wooden table facing the Douro"),
    _row(123, "Ambience Session", "Vienna Coffeehouse", 8, "Vienna Coffeehouse • Warm Focus", 0.05, 0.09, False, False, "cafe velvet marble", "grand Viennese coffeehouse with marble tables, dark wood booths, brass lamps, laptop beside a ceramic mug"),
    _row(124, "Ambience Session", "Melbourne Laneway", 6, "Melbourne Laneway • Coffee Focus", 0.07, 0.08, False, False, "laneway coffee brick", "narrow Melbourne laneway cafe, graffiti walls outside the window, warm Edison bulbs, laptop on a communal table"),
    _row(125, "Ambience Session", "Brooklyn Brownstone", 8, "Brooklyn Brownstone • Warm Evening", 0.06, 0.07, False, False, "brownstone amber evening", "Brooklyn brownstone parlor converted to a desk, bay window, warm floor lamp, laptop on a vintage desk"),
    _row(126, "Ambience Session", "Barcelona Terrace", 6, "Barcelona Terrace • Golden Hour", 0.04, 0.07, False, False, "terrace golden plants", "Barcelona apartment terrace at golden hour, potted plants, warm city light, laptop on a small iron table"),
    _row(127, "Ambience Session", "Prague Old Town", 8, "Prague Old Town • Warm Night", 0.06, 0.08, False, False, "old-town amber lamps", "Prague old-town apartment, leaded window over cobblestones, warm table lamp, laptop and ceramic mug"),
    _row(128, "Ambience Session", "Edinburgh Close", 8, "Edinburgh Close • Cozy Rain", 0.09, 0.07, False, False, "stone close rain cozy", "Edinburgh close apartment, rain on a stone-framed window, tartan throw, warm lamp, laptop on a worn desk"),
    _row(129, "Ambience Session", "Montreal Winter Cafe", 8, "Montreal Winter • Cozy Cafe", 0.04, 0.08, False, False, "winter cafe cozy snow", "Montreal cafe in winter, frost at the window edges, warm interior lamps, laptop beside a ceramic mug"),
    _row(130, "Ambience Session", "Taipei Night Market Desk", 6, "Taipei Night Market • Warm Glow", 0.05, 0.06, False, False, "lantern night-market warm", "small Taipei apartment above a night market, lantern glow through the window, warm desk lamp, laptop"),
    _row(131, "Ambience Session", "Istanbul Bosphorus", 8, "Istanbul Bosphorus • Warm Evening", 0.05, 0.07, False, False, "bosphorus ferry warm", "Istanbul apartment overlooking the Bosphorus at evening, warm lamps, ferry lights, laptop on a low table"),
    _row(132, "Rainy Night Coding", "Osaka Alley", 8, "Osaka Alley • Rain Focus", 0.11, 0.03, False, False, "rain alley neon puddles", "Osaka back-alley apartment at night, rain-streaked window, wet pavement reflections, laptop as the main light"),
    _row(133, "Rainy Night Coding", "Vancouver Harbor", 8, "Vancouver Harbor • Rain Focus", 0.10, 0.04, False, False, "harbor rain glass", "Vancouver high-rise desk facing a rainy harbor, rain on floor-to-ceiling glass, warm task lamp, laptop"),
    _row(134, "Rainy Night Coding", "Dublin Georgian", 8, "Dublin Georgian • Night Rain", 0.10, 0.05, False, False, "georgian rain sash-window", "Dublin Georgian room, tall sash window with rain, dark wood desk, warm lamp, laptop and notebooks"),
    _row(135, "Rainy Night Coding", "Chicago Loop", 8, "Chicago Loop • Storm Focus", 0.12, 0.0, False, True, "storm high-rise rain", "Chicago Loop apartment in a storm, rain hammering the glass, distant skyscraper lights, laptop glow"),
    _row(136, "Rainy Night Coding", "Manchester Brick", 6, "Manchester Brick • Rain Focus", 0.10, 0.04, False, False, "brick mill rain", "Manchester mill conversion, brick walls, rain on industrial windows, warm lamp, laptop on a steel desk"),
    _row(137, "Rainy Night Coding", "Singapore Monsoon", 8, "Singapore Monsoon • Heavy Rain", 0.13, 0.02, False, False, "monsoon tropical rain", "Singapore HDB desk during monsoon, heavy rain on the window, tropical night, warm interior lamp, laptop"),
    _row(138, "Rainy Night Coding", "Portland Attic", 8, "Portland Attic • Quiet Rain", 0.09, 0.04, False, False, "attic rain sloped-window", "Portland attic studio, sloped rain window, fairy lights, warm lamp, laptop on a low desk"),
    _row(139, "Rainy Night Coding", "Busan Harbor Fog", 8, "Busan Harbor • Rain Fog", 0.11, 0.0, False, True, "harbor fog rain", "Busan coastal apartment, rain and fog over the harbor, neon signs blurred, laptop glow on the desk"),
    _row(140, "Rainy Night Coding", "Glasgow Tenement", 6, "Glasgow Tenement • Rain Focus", 0.10, 0.04, False, False, "tenement rain sandstone", "Glasgow tenement room, rain on a bay window, sandstone buildings outside, warm lamp, laptop"),
    _row(141, "Rainy Night Coding", "Hoboken Pier", 8, "Hoboken Pier • Night Rain", 0.10, 0.03, False, False, "pier manhattan rain", "Hoboken apartment facing Manhattan in the rain, wet pier lights, warm desk lamp, laptop"),
    _row(142, "Rainy Night Coding", "Kyoto Machiya Rain", 8, "Kyoto Machiya • Quiet Rain", 0.09, 0.03, False, False, "machiya rain wood", "Kyoto machiya interior, rain on a wooden lattice window, tatami edge, warm lamp, laptop on a low table"),
    _row(143, "Rainy Night Coding", "Rotterdam Docks", 8, "Rotterdam Docks • Rain Focus", 0.11, 0.02, False, False, "docks cranes rain", "Rotterdam loft facing rainy docks, cranes and water, industrial window, warm lamp, laptop"),
    _row(144, "Cabin Programmer", "Alpine Chalet", 10, "Alpine Chalet • Fireplace Snow", 0.03, 0.0, False, True, "chalet fireplace snow", "Alpine chalet interior, stone fireplace, snow falling outside the window, wooden desk, laptop"),
    _row(145, "Cabin Programmer", "Vermont Snow", 8, "Vermont Snow • Cozy Cabin", 0.03, 0.0, False, True, "vermont snow pines", "Vermont log cabin, snow-laden pines outside, wood stove glow, wool blanket, laptop on a rustic desk"),
    _row(146, "Cabin Programmer", "Norwegian Fjord", 8, "Norwegian Fjord • Winter Cabin", 0.02, 0.0, False, True, "fjord winter snow", "Norwegian cabin facing a winter fjord, snow on the glass, warm wood interior, laptop by the window"),
    _row(147, "Cabin Programmer", "Canadian Rockies", 10, "Canadian Rockies • Fireplace Night", 0.03, 0.0, False, True, "rockies fireplace snow", "Canadian Rockies cabin at night, fireplace, snow against the window, pine beams, laptop on a thick wooden table"),
    _row(148, "Cabin Programmer", "Scottish Bothy", 6, "Scottish Bothy • Cozy Fire", 0.04, 0.0, False, True, "bothy fire snow", "Scottish bothy interior, peat fire, snow outside a small window, simple wooden desk, laptop"),
    _row(149, "Cabin Programmer", "Tahoe Cabin", 8, "Tahoe Cabin • Snow Focus", 0.03, 0.0, False, True, "tahoe snow lake", "Lake Tahoe cabin, snow outside, lake barely visible, warm lamps, laptop on a pine desk"),
    _row(150, "Cabin Programmer", "Hokkaido Onsen Desk", 8, "Hokkaido Onsen • Winter Warmth", 0.03, 0.0, False, True, "hokkaido snow paper-screen", "Hokkaido inn room, snow garden outside paper screens, warm interior, low table with a laptop"),
    _row(151, "Cabin Programmer", "Patagonia Lodge", 8, "Patagonia Lodge • Fireplace", 0.02, 0.0, False, True, "patagonia fireplace wind", "Patagonia lodge, huge window to mountains, fireplace, wind-blown snow, laptop on a long wooden table"),
    _row(152, "Dark Mode Workspace", "Triple Monitor", 8, "Triple Monitor • RGB Glow", 0.0, 0.0, True, True, "triple-monitor rgb dark", "dark bedroom workspace, triple monitors with blurred colorful code, subtle RGB underglow, no people"),
    _row(153, "Dark Mode Workspace", "OLED Cave", 8, "OLED Cave • Pure Dark", 0.0, 0.0, True, True, "oled cave dark", "nearly black room, single ultrawide OLED, faint desk lamp, floating dust in the screen light, laptop and keyboard"),
    _row(154, "Dark Mode Workspace", "Mechanical Keyboard", 6, "Mechanical Keyboard • Night Flow", 0.0, 0.0, True, True, "mechanical keys dark", "close developer desk at night, mechanical keyboard, dark wood, monitor glow, cable-managed workspace"),
    _row(155, "Dark Mode Workspace", "Battlestation", 8, "Battlestation • RGB Night", 0.0, 0.0, True, True, "battlestation rgb neon", "full battlestation desk, RGB keyboard underglow, dual monitors, dark wall, neon accent strip"),
    _row(156, "Linux Hacker Room", "Homelab Rack", 8, "Homelab Rack • Server Hum", 0.0, 0.0, True, True, "homelab rack servers", "homelab room, 19-inch server rack with blinking LEDs, desk with Linux terminals on screen, dark walls"),
    _row(157, "Linux Hacker Room", "Server Closet RGB", 6, "Server Closet • RGB Hum", 0.0, 0.0, True, True, "server closet rgb", "small server closet converted to a desk, RGB strips, network switches, laptop with a terminal"),
    _row(158, "Linux Hacker Room", "Raspberry Cluster", 4, "Raspberry Cluster • Tiny Homelab", 0.0, 0.0, True, True, "raspberry cluster leds", "desk with a Raspberry Pi cluster, blinking LEDs, mechanical keyboard, dark room, monitor with code"),
    _row(159, "Linux Hacker Room", "Neon Terminal Wall", 8, "Neon Terminal • Synth Night", 0.0, 0.0, True, True, "neon terminal synth", "hacker room with a neon-lit wall of terminals, dark desk, RGB keyboard, city glow through blinds"),
    _row(160, "Linux Hacker Room", "Arch Tiling Night", 6, "Arch Tiling • Night Zen", 0.0, 0.0, True, True, "tiling rice dark", "minimal Linux rice setup at night, tiling window manager on a monitor, plants, dark desk, no RGB overload"),
    _row(161, "Cyberpunk Developer Room", "Synthwave Desk", 8, "Synthwave Desk • Neon Focus", 0.0, 0.0, True, True, "synthwave neon grid", "synthwave developer room, magenta and cyan neon, grid wall art, desk with a glowing monitor, dark city through blinds"),
    _row(162, "Cyberpunk Developer Room", "Neon Alley Loft", 8, "Neon Alley • Rain Haze", 0.10, 0.0, False, True, "neon alley rain", "cyberpunk loft above a neon alley, rain on the window, holographic signs, desk with laptop glow"),
    _row(163, "Cyberpunk Developer Room", "Mega City 2AM", 8, "Mega City • 2AM Haze", 0.08, 0.0, False, True, "megacity haze neon", "high-rise cyberpunk apartment at 2AM, dense neon city, rain haze, ultrawide monitor, dark interior"),
    _row(164, "Cyberpunk Developer Room", "Holo Billboard", 6, "Holo Billboard • Night Code", 0.07, 0.0, False, True, "billboard hologram neon", "desk facing a huge holographic billboard through rain-speckled glass, neon interior strips, laptop"),
    _row(165, "Cyberpunk Developer Room", "Maglev Window", 8, "Maglev Window • Neon Transit", 0.09, 0.0, False, True, "maglev neon rain", "apartment window over a maglev line, neon rain, passing train lights, developer desk in the foreground"),
    _row(166, "Space Programming Session", "ISS Cupola", 8, "ISS Cupola • Orbital Focus", 0.0, 0.0, True, True, "iss cupola earth", "ISS cupola workstation, Earth curve through windows, floating laptop velcroed to a panel, no people"),
    _row(167, "Space Programming Session", "Orbital Lab", 8, "Orbital Lab • Quiet Drift", 0.0, 0.0, True, True, "orbital lab modules", "orbital laboratory module, white panels, laptop on a restraint tray, Earth light through a small porthole"),
    _row(168, "Space Programming Session", "Titan Outpost", 6, "Titan Outpost • Orange Haze", 0.0, 0.0, True, True, "titan haze outpost", "Titan surface outpost interior, orange haze through thick glass, industrial desk, laptop with code"),
    _row(169, "Space Programming Session", "Lagrange Station", 10, "Lagrange Station • Deep Space", 0.0, 0.0, True, True, "lagrange station stars", "Lagrange point station lounge-desk, starfield window, soft instrument lights, laptop on a metal table"),
    _row(170, "Space Programming Session", "Europa Ice Base", 8, "Europa Ice Base • Quiet Dark", 0.0, 0.0, True, True, "europa ice base", "Europa ice-base control desk, dark ice through a thick viewport, blue instrument glow, laptop"),
    _row(171, "Space Programming Session", "Saturn Rings View", 8, "Saturn Rings • Orbital Night", 0.0, 0.0, True, True, "saturn rings orbital", "observation deck facing Saturn rings, workstation with a laptop, dim cabin lights, no people"),
    _row(172, "Deep Work Sessions", "Morning Courtyard", 6, "Morning Courtyard • Sunrise Focus", 0.0, 0.04, True, False, "courtyard sunrise birds", "sunny courtyard studio at morning, plants, birds outside, soft sunrise light, laptop on a clean desk"),
    _row(173, "Deep Work Sessions", "Sunrise Loft", 8, "Sunrise Loft • First Light", 0.0, 0.03, True, False, "loft sunrise linen", "white loft at sunrise, linen curtains, plants, warm first light, laptop on a pale wooden desk"),
    _row(174, "Deep Work Sessions", "Lake House", 8, "Lake House • Water Focus", 0.0, 0.0, True, True, "lake house water", "lake house study, wide window to still water, morning light, wooden desk, laptop"),
    _row(175, "Deep Work Sessions", "Beach House Desk", 6, "Beach House • Tide Focus", 0.0, 0.0, True, True, "beach house tide", "beach house desk facing the ocean, gentle morning light, linen, laptop, no people on the sand"),
    _row(176, "Deep Work Sessions", "Forest Window", 8, "Forest Window • Morning Birds", 0.0, 0.0, True, True, "forest birds foliage", "cabin study facing dense forest, morning birds implied by foliage, sun shafts, laptop on a wood desk"),
    _row(177, "Deep Work Sessions", "Desert Adobe", 6, "Desert Adobe • Quiet Heat", 0.0, 0.0, True, True, "adobe desert quiet", "adobe desert studio, thick walls, a small window to dunes, laptop on a clay-toned desk"),
    _row(178, "Deep Work Sessions", "Cliffside Studio", 8, "Cliffside Studio • Water Light", 0.0, 0.0, True, True, "cliffside water studio", "cliffside studio, ocean far below, bright water light, minimal desk, laptop"),
    _row(179, "Silent Library for Deep Work", "Reading Carrel", 8, "Reading Carrel • Timeless Quiet", 0.0, 0.0, True, True, "carrel green-lamp books", "library reading carrel, green banker lamp, stacks of books, laptop with blurred code, no people"),
    _row(180, "Silent Library for Deep Work", "Law Library", 8, "Law Library • Night Quiet", 0.0, 0.0, True, True, "law-library oak night", "university law library at night, oak tables, high windows, green lamps, laptop"),
    _row(181, "Silent Library for Deep Work", "Monastery Script", 6, "Monastery Script • Still Hours", 0.0, 0.0, True, True, "monastery stone desk", "monastery scriptorium desk, stone walls, a slit window, laptop anachronistically on aged wood"),
    _row(182, "Silent Library for Deep Work", "British Library", 8, "British Library • Deep Quiet", 0.0, 0.0, True, True, "british-library dome desks", "vast library hall, desk lamp, laptop among closed books, no readable titles, empty chairs"),
    _row(183, "Startup Office at Midnight", "Seed Round Night", 6, "Seed Round • After Hours", 0.0, 0.04, True, False, "startup night kitchen", "startup office at midnight, empty open space, kitchen lights, laptop on a standing desk"),
    _row(184, "Startup Office at Midnight", "Kitchen After Hours", 4, "Kitchen After Hours • Quiet Build", 0.0, 0.05, True, False, "office-kitchen midnight", "startup kitchen table at night, leftover mugs, laptop, glass wall to a dark office"),
    _row(185, "Startup Office at Midnight", "Ping Pong Dark", 6, "Ping Pong Dark • Founder Mode", 0.0, 0.0, True, True, "ping-pong dark office", "startup loft at night, ping pong table in the background, desk with laptop, city lights"),
    _row(186, "Late Night Debugging", "Incident Bridge", 3, "Incident Bridge • Calm Adrenaline", 0.0, 0.0, True, True, "incident monitors dark", "dark on-call room, multiple monitors with blurred dashboards, coffee mug, laptop, no people"),
    _row(187, "Late Night Debugging", "On Call Couch", 4, "On Call Couch • 3AM Quiet", 0.0, 0.0, True, True, "couch laptop 3am", "living room at 3AM, laptop on a coffee table, TV off, single lamp, debugging session mood"),
    _row(188, "Late Night Debugging", "Deploy Window", 3, "Deploy Window • Night Watch", 0.0, 0.0, True, True, "deploy terminal night", "desk at night during a deploy window, terminal-heavy monitor, status lights, empty office behind"),
    _row(189, "AI Research Lab", "GPU Cluster", 8, "GPU Cluster • Blue Light", 0.0, 0.0, True, True, "gpu cluster blue", "AI lab, GPU server cluster with blue LEDs, researcher desk with laptop, dark glass walls"),
    _row(190, "AI Research Lab", "Whiteboard Dawn", 6, "Whiteboard Dawn • Morning Lab", 0.0, 0.0, True, True, "whiteboard dawn lab", "research lab at dawn, empty whiteboard, laptop on a bench, first light through blinds"),
    _row(191, "AI Research Lab", "Quiet Lab Bench", 8, "Quiet Lab Bench • Server Glow", 0.0, 0.0, True, True, "lab bench servers", "quiet lab bench, oscilloscope-like lights out of focus, laptop, server rack glow in the background"),
    _row(192, "Lounge Coding Sessions", "Vinyl Corner", 8, "Vinyl Corner • Warm Night", 0.0, 0.04, True, False, "vinyl lounge warm", "lounge corner with vinyl shelves, warm lamps, record player, laptop on a low table"),
    _row(193, "Lounge Coding Sessions", "Hotel Lobby Night", 6, "Hotel Lobby • Late Code", 0.0, 0.05, True, False, "hotel lobby night", "quiet hotel lobby at night, leather chairs, warm lamps, laptop on a side table"),
    _row(194, "Lounge Coding Sessions", "Jazz Club Booth", 8, "Jazz Club Booth • After Hours", 0.0, 0.04, True, False, "jazz booth warm", "empty jazz club booth after hours, stage lights dim, laptop on a small table, brass and wood"),
    _row(195, "Seasonal", "Spring Rain Study", 8, "Spring Rain • Fresh Focus", 0.09, 0.04, False, False, "spring rain blossoms", "spring study, rain on the window, wet blossoms outside, warm lamp, laptop on a pale desk"),
    _row(196, "Seasonal", "Autumn Library", 8, "Autumn Library • Falling Quiet", 0.0, 0.0, True, True, "autumn library leaves", "library desk in autumn, window to falling leaves, warm lamps, laptop, stacked books"),
    _row(197, "Seasonal", "Winter Solstice Code", 10, "Winter Solstice • Cozy Night", 0.03, 0.0, False, True, "solstice cozy fireplace", "winter solstice night desk, fireplace, snow at the window, warm lamps, laptop"),
    _row(198, "Seasonal", "Golden Hour Remote", 6, "Golden Hour • Morning Remote", 0.0, 0.04, True, False, "golden-hour remote morning", "remote-work apartment at golden hour morning, plants, sunrise on the wall, laptop on a dining table"),
    _row(199, "Ambience Session", "Lisbon Tram Night", 8, "Lisbon Tram • Warm Night", 0.06, 0.08, False, False, "lisbon tram tiles warm", "Lisbon apartment at night, tram tracks below the window, azulejo walls, warm lamp, laptop"),
    _row(200, "Rainy Night Coding", "Hong Kong Tram", 8, "Hong Kong Tram • Rain Night", 0.11, 0.03, False, False, "hongkong tram rain neon", "Hong Kong apartment, rain, tram and neon below, cramped warm desk, laptop"),
    _row(201, "Cabin Programmer", "Fireplace Reading", 8, "Fireplace Reading • Cozy Code", 0.03, 0.0, False, True, "fireplace reading snow", "cabin reading nook, fireplace, snow window, laptop on a side table instead of a book"),
    _row(202, "Dark Mode Workspace", "Minimal Walnut", 6, "Minimal Walnut • Quiet Dark", 0.0, 0.0, True, True, "walnut minimal dark", "minimal walnut desk, single monitor, dark wall, tiny lamp, no RGB"),
    _row(203, "Linux Hacker Room", "Homelab Basement", 8, "Homelab Basement • Fan Hum", 0.0, 0.0, True, True, "basement homelab servers", "basement homelab, concrete, server rack, desk with terminals, cool LED light"),
    _row(204, "Cyberpunk Developer Room", "Synthwave Rain", 8, "Synthwave Rain • Neon Wet", 0.11, 0.0, False, True, "synthwave rain neon", "synthwave room, rain on a neon-framed window, magenta-cyan lighting, desk with a glowing monitor"),
    _row(205, "Space Programming Session", "Deep Space Radio", 8, "Deep Space Radio • Orbital Hum", 0.0, 0.0, True, True, "deep-space radio dish", "spacecraft radio room, dish controls out of focus, starfield window, laptop on a console"),
    _row(206, "Deep Work Sessions", "Ocean Tide", 8, "Ocean Tide • Water Focus", 0.0, 0.0, True, True, "ocean tide window", "cliff house, ocean tide through a wide window, soft daylight, laptop on a driftwood-toned desk"),
    _row(207, "Silent Library for Deep Work", "Candle Carrel", 6, "Candle Carrel • Night Quiet", 0.0, 0.0, True, True, "candle carrel books", "private library carrel, candle-like warm lamps, old books, laptop, no open flame smoke"),
    _row(208, "Startup Office at Midnight", "Empty Floor", 8, "Empty Floor • After Hours", 0.0, 0.03, True, False, "empty floor glass night", "entire empty startup floor at night, glass walls, one desk lamp, laptop"),
    _row(209, "Late Night Debugging", "Dual Terminal", 4, "Dual Terminal • Night Flow", 0.0, 0.0, True, True, "dual terminal dark", "dual-monitor terminal setup at night, dark room, mug, glowing code that stays unreadable"),
    _row(210, "AI Research Lab", "Server Aisle", 8, "Server Aisle • Cold Blue", 0.0, 0.0, True, True, "server aisle cold", "data-center aisle beside a small standing desk, cold blue LEDs, laptop"),
    _row(211, "Lounge Coding Sessions", "Speakeasy Desk", 8, "Speakeasy Desk • Warm Night", 0.0, 0.05, True, False, "speakeasy wood warm", "speakeasy back-room desk, dark wood, warm lamps, laptop, bottles blurred in the background"),
    _row(212, "Ambience Session", "Warm Mug Rainy Window", 8, "Warm Mug • Rainy Window", 0.09, 0.08, False, False, "mug rain warm window", "developer desk, ceramic mug, rain-streaked window, warm lamp, laptop with blurred code"),
    _row(213, "Rainy Night Coding", "Tokyo Capsule", 6, "Tokyo Capsule • Rain Night", 0.10, 0.02, False, False, "capsule tokyo rain", "tiny Tokyo capsule-hotel style desk, rain city through a small window, laptop as the only light"),
    _row(214, "Cabin Programmer", "Cozy Wool Blanket", 8, "Cozy Wool • Winter Cabin", 0.03, 0.0, False, True, "wool cozy snow", "cabin desk with a wool blanket on the chair, snow window, fireplace glow, laptop"),
    _row(215, "Deep Work Sessions", "Morning Birds Garden", 6, "Morning Birds • Garden Focus", 0.0, 0.0, True, True, "garden birds sunrise", "garden-facing study at sunrise, foliage, bird-friendly trees outside, laptop on a white desk"),
    _row(216, "Cyberpunk Developer Room", "RGB Alley", 8, "RGB Alley • Neon Night", 0.09, 0.0, False, True, "rgb alley neon", "desk against a window over an RGB-lit alley, neon puddles, dark interior, laptop"),
    _row(217, "Space Programming Session", "Orbital Sunrise", 8, "Orbital Sunrise • Station Morning", 0.0, 0.0, True, True, "orbital sunrise station", "space station corridor desk, orbital sunrise flaring through a porthole, laptop on a tray"),
    _row(218, "Linux Hacker Room", "Neon Homelab", 8, "Neon Homelab • Server Night", 0.0, 0.0, True, True, "neon homelab rack", "homelab with neon accent lighting, server rack, mechanical keyboard, terminal monitors"),
    _row(219, "Deep Work Sessions", "Lake Sunrise", 8, "Lake Sunrise • Water Morning", 0.0, 0.0, True, True, "lake sunrise mist", "lake cabin at sunrise, mist over water, warm interior, laptop on a window desk"),
    _row(220, "Ambience Session", "Paris Rain Cafe", 8, "Paris Rain Cafe • Warm Focus", 0.09, 0.08, False, False, "paris cafe rain warm", "Paris cafe window seat in the rain, warm interior, laptop, ceramic mug, wet boulevard outside"),
    _row(221, "Seasonal", "New Moon Focus", 8, "New Moon • Deep Night", 0.0, 0.0, True, True, "new-moon dark quiet", "dark rural desk under a new moon, almost no outside light, single warm lamp, laptop"),
)


def scene_prompt_for(concept: CatalogConcept) -> str:
    return (
        f"Photorealistic {concept.visual}, "
        "developer workspace with laptop showing colorful blurred code completely unreadable, "
        "no people, no readable text, ceramic mug without steam if a mug is present, "
        "no steam, no smoke, no vapor wisps, no fog plumes, "
        "shallow depth of field, 16:9 aspect ratio"
    )
