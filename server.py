<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Exuma Accommodations</title>

<!-- Leaflet map styles -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />

<style>
html { scroll-behavior: smooth; }
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; background: #f5f8fa; color: #222; }

header {
    background: #006994;
    color: white;
    padding: 18px 20px;
    position: sticky;
    top: 0;
    z-index: 10;
}
header nav {
    max-width: 1200px;
    margin: auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
}
header a { color: white; text-decoration: none; font-weight: bold; }

.container { max-width: 1200px; margin: auto; padding: 25px 18px 50px; }
.page-title { text-align: center; margin-bottom: 35px; }
.page-title h1 { margin-bottom: 8px; color: #005b7a; }

.region { margin-bottom: 50px; }
.region-title {
    background: #007ea7;
    color: white;
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 20px;
}
.region-title h2 { margin: 0; }
.region-title p { margin: 5px 0 0; }

.region-map-wrap {
    margin: 0 0 22px;
    padding: 12px;
    background: #fff;
    border: 1px solid #dbe5e9;
    border-radius: 12px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.08);
}
.region-map-title {
    margin: 0 0 10px;
    color: #005b7a;
    font-size: 16px;
}
.region-map {
    width: 100%;
    height: 300px;
    border-radius: 8px;
    z-index: 1;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 22px;
}

.card {
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 3px 12px rgba(0,0,0,0.12);
    border: 1px solid #e1e1e1;
}
.card h3 { margin: 0; padding: 15px 15px 5px; color: #005b7a; }
.card-location { padding: 0 15px 12px; color: #666; font-size: 14px; }

.accommodation-description {
    margin: 10px 0 15px;
    padding: 0 15px;
    color: #555;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-line;
}

.info { padding: 14px 15px 5px; }
.price { font-size: 18px; font-weight: bold; color: #007ea7; }

.gallery {
    display: flex;
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-snap-type: x mandatory;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    gap: 0;
}
.gallery::-webkit-scrollbar { display: none; }

.gallery-item {
    flex: 0 0 100%;
    width: 100%;
    position: relative;
    scroll-snap-align: start;
    scroll-snap-stop: always;
}

.gallery img {
    width: 100%;
    height: 420px;
    object-fit: cover;
    display: block;
    cursor: zoom-in;
}

.gallery-label {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.55);
    color: #fff;
    font-size: 13px;
    font-weight: 600;
    text-align: center;
    padding: 8px 4px;
    pointer-events: none;
}

.reserve-btn {
    display: block;
    width: 100%;
    padding: 13px 18px;
    background: #007ea7;
    color: white;
    text-align: center;
    text-decoration: none;
    font-weight: 600;
    border-radius: 12px;
    margin-top: 15px;
    transition: 0.2s ease;
}
.reserve-btn:hover { background: #006994; transform: translateY(-1px); }

.company-intro {
    width: 100%;
    background: linear-gradient(135deg, #087b89, #119ca3);
    border-bottom: 1px solid #08727f;
    padding: 28px 18px;
}
.company-intro-inner { max-width: 1100px; margin: 0 auto; }
.company-intro h1 { color: #fff; margin: 0 0 14px; font-size: 30px; line-height: 1.2; }
.company-intro p { color: #fff; margin: 0 0 12px; font-size: 15px; line-height: 1.7; }
.company-intro p:last-child { margin-bottom: 0; }

/* Small white footnote */
.company-footnote {
    width: 100%;
    background: #ffffff;
    color: #666666;
    text-align: center;
    padding: 25px 10px 20px;
    margin-top: 40px;
    border-top: 1px solid #eeeeee;
    font-size: 11px;
    line-height: 1.5;
}
.company-footnote p { margin: 2px 0; }
.company-footnote strong { color: #444444; }
.company-footnote a { color: #007c91; text-decoration: none; }
.company-footnote a:hover { text-decoration: underline; }

/* Lightbox */
.lightbox {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0,0,0,0.92);
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.lightbox.open { display: flex; }

.lightbox-img {
    max-width: 95vw;
    max-height: 85vh;
    object-fit: contain;
    border-radius: 6px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6);
    user-select: none;
}

.lightbox-caption {
    position: absolute;
    bottom: 22px;
    left: 0;
    right: 0;
    text-align: center;
    color: #fff;
    font-size: 14px;
    padding: 0 60px;
    line-height: 1.5;
    pointer-events: none;
}
.lightbox-caption .lb-name { font-weight: 700; display: block; margin-bottom: 2px; }
.lightbox-caption .lb-label {
    color: #b8d8e0;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.lightbox-close,
.lightbox-prev,
.lightbox-next {
    position: absolute;
    background: rgba(255,255,255,0.15);
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 26px;
    line-height: 1;
    padding: 12px 16px;
    border-radius: 50%;
    transition: background 0.2s ease;
    -webkit-tap-highlight-color: transparent;
}
.lightbox-close:hover,
.lightbox-prev:hover,
.lightbox-next:hover { background: rgba(255,255,255,0.3); }

.lightbox-close { top: 18px; right: 18px; font-size: 22px; padding: 10px 15px; }
.lightbox-prev { left: 18px; top: 50%; transform: translateY(-50%); }
.lightbox-next { right: 18px; top: 50%; transform: translateY(-50%); }
.lightbox-prev:disabled,
.lightbox-next:disabled { opacity: 0.25; cursor: default; }

@media (max-width: 900px) {
    .gallery img { height: 340px; }
}

@media (max-width: 600px) {
    header nav { flex-direction: column; align-items: flex-start; }
    .gallery img { height: 260px; }
    .gallery-label { font-size: 11px; padding: 6px 2px; }
    .company-intro { padding: 22px 15px; }
    .company-intro h1 { font-size: 25px; }
    .company-intro p { font-size: 14px; line-height: 1.65; }
    .lightbox-prev, .lightbox-next { font-size: 20px; padding: 10px 13px; }
    .lightbox-close { top: 12px; right: 12px; font-size: 18px; padding: 8px 12px; }
    .lightbox-prev { left: 8px; }
    .lightbox-next { right: 8px; }
    .lightbox-caption { bottom: 14px; padding: 0 50px; font-size: 12px; }
}


/* Refined, consistent spacing for a polished hospitality-business layout */
:root {
    --page-gutter: clamp(18px, 4vw, 42px);
    --section-space: clamp(34px, 5vw, 56px);
    --card-radius: 14px;
}
body { line-height: 1.55; }
.company-intro { padding: clamp(34px, 5vw, 58px) var(--page-gutter); }
.company-intro-inner { max-width: 1120px; }
.company-intro h1 { margin-bottom: 18px; letter-spacing: -0.025em; }
.company-intro p { max-width: 900px; margin-bottom: 14px; }
header { padding: 16px var(--page-gutter); }
header nav { min-height: 34px; gap: 22px; }
header nav a { display: inline-flex; align-items: center; min-height: 42px; }
.container { max-width: 1280px; padding: clamp(28px, 4vw, 48px) var(--page-gutter) 64px; }
.page-title { max-width: 760px; margin: 0 auto 42px; }
.page-title h1 { line-height: 1.2; margin: 0 0 12px; letter-spacing: -0.025em; }
.region { margin-bottom: var(--section-space); }
.region-title { padding: 20px 24px; border-radius: 12px; margin-bottom: 24px; }
.region-title h2 { line-height: 1.25; letter-spacing: -0.01em; }
.region-title p { line-height: 1.55; margin-top: 8px; }
.region-map-wrap { margin-bottom: 28px; padding: 16px; border-radius: 14px; }
.region-map-title { margin: 0 0 14px; line-height: 1.4; }
.region-map { height: clamp(240px, 30vw, 340px); border-radius: 10px; }
.grid { grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 28px; align-items: stretch; }
.card { display: flex; flex-direction: column; min-width: 0; border-radius: var(--card-radius); box-shadow: 0 5px 22px rgba(20, 48, 62, 0.08); border-color: #e3eaee; transition: box-shadow .2s ease, transform .2s ease; }
.card:hover { box-shadow: 0 10px 28px rgba(20, 48, 62, 0.13); transform: translateY(-2px); }
.card h3 { padding: 20px 20px 7px; font-size: 19px; line-height: 1.35; }
.card-location { padding: 0 20px 14px; font-size: 13px; line-height: 1.45; }
.accommodation-description { margin: 0; padding: 4px 20px 18px; font-size: 14px; line-height: 1.75; color: #53616a; white-space: pre-line; flex: 1 0 auto; }
.info { padding: 18px 20px 20px; margin-top: auto; border-top: 1px solid #edf1f3; }
.price { font-size: 18px; line-height: 1.4; letter-spacing: -0.01em; }
.gallery img { height: clamp(240px, 27vw, 340px); }
.reserve-btn { min-height: 48px; display: flex; align-items: center; justify-content: center; padding: 13px 18px; margin-top: 16px; border-radius: 8px; letter-spacing: .01em; }
.company-footnote { margin-top: 0; padding: 30px var(--page-gutter) 26px; line-height: 1.7; }
@media (min-width: 1100px) {
    .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 760px) {
    .grid { gap: 20px; }
    .region-title { padding: 18px 20px; }
    .region-map-wrap { padding: 10px; }
    .card h3 { padding: 18px 18px 6px; }
    .card-location { padding: 0 18px 12px; }
    .accommodation-description { padding: 4px 18px 16px; }
    .info { padding: 16px 18px 18px; }
    .gallery img { height: clamp(230px, 62vw, 320px); }
}
@media (max-width: 600px) {
    header nav { gap: 8px; }
    .container { padding-top: 26px; padding-bottom: 42px; }
    .page-title { margin-bottom: 30px; }
    .region { margin-bottom: 38px; }
    .company-intro { padding: 30px 20px; }
    .company-intro h1 { font-size: 26px; }
    .company-intro p { line-height: 1.75; }
    .region-map { height: 240px; }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; }
}

</style>
</head>

<body>

<section class="company-intro">
    <div class="company-intro-inner">
        <h1>Exuma Sport Coast Service</h1>
        <p>
            <strong>Exuma Sport Coast Service</strong> is the accommodation
            service featured on this platform, helping visitors discover
            comfortable places to stay while exploring the beautiful islands
            and communities of Exuma, Bahamas. Our accommodation selection
            covers areas including George Town, Moss Town, Staniel Cay,
            Michelson/Roker's Point and other destinations throughout Exuma.
        </p>
        <p>
            Whether you are visiting for a relaxing beach holiday, an island
            adventure, water activities or a longer stay, Exuma Sport Coast
            Service provides accommodation options designed to make your
            Exuma experience convenient and enjoyable. Browse available
            properties, view their living rooms, bedrooms and bathrooms, and
            choose the accommodation that best suits your trip.
        </p>
    </div>
</section>

<header>
    <nav>
        <a href="index.html">← Back to Home</a>
        <strong>Exuma Accommodations</strong>
    </nav>
</header>

<main class="container">

<div class="page-title">
    <h1>Available Accommodations</h1>
    <p>Explore comfortable stays across beautiful Exuma.</p>
</div>

<!-- GEORGE TOWN -->
<section class="region" id="george-town">
<div class="region-title">
<h2>George Town</h2>
<p>Comfortable accommodation options in George Town, Great Exuma.</p>
</div>
<div class="region-map-wrap"><h3 class="region-map-title">George Town location</h3><div class="region-map" id="map-george-town" aria-label="Map showing George Town, Exuma"></div></div>
<div class="grid" id="grid-george-town"></div>
</section>

<!-- LUXURY -->
<section class="region" id="luxury-villas">
<div class="region-title">
<h2>Luxury Accommodations</h2>
<p>Premium accommodation options for an unforgettable Exuma stay.</p>
</div>
<div class="region-map-wrap"><h3 class="region-map-title">Exuma location</h3><div class="region-map" id="map-luxury" aria-label="Map of Exuma for luxury accommodations"></div></div>
<div class="grid" id="grid-luxury"></div>
</section>

<!-- MICHELSON -->
<section class="region" id="michelson-rokers-point">
<div class="region-title">
<h2>Michelson</h2>
<p>Relaxing accommodation options in the Michelson area.</p>
</div>
<div class="region-map-wrap"><h3 class="region-map-title">Michelson location</h3><div class="region-map" id="map-michelson" aria-label="Map showing Michelson, Exuma"></div></div>
<div class="grid" id="grid-michelson"></div>
</section>

<!-- MOSS TOWN -->
<section class="region" id="moss-town">
<div class="region-title">
<h2>Moss Town</h2>
<p>Comfortable accommodation options in Moss Town, Great Exuma.</p>
</div>
<div class="region-map-wrap"><h3 class="region-map-title">Moss Town location</h3><div class="region-map" id="map-moss" aria-label="Map showing Moss Town, Exuma"></div></div>
<div class="grid" id="grid-moss"></div>
</section>

<!-- STANIEL CAY -->
<section class="region" id="staniel-cay-exuma-cays">
<div class="region-title">
<h2>Staniel Cay</h2>
<p>Stay near one of the most beautiful areas of the Exuma Cays.</p>
</div>
<div class="region-map-wrap"><h3 class="region-map-title">Staniel Cay location</h3><div class="region-map" id="map-staniel" aria-label="Map showing Staniel Cay, Exuma Cays"></div></div>
<div class="grid" id="grid-staniel"></div>
</section>

</main>

<!-- Small white footnote -->
<section class="company-footnote">
    <p>
        <strong>Exuma Sport Coast Service</strong> · Exuma, Bahamas ·
        <a href="mailto:exumaaccomodations@gmail.com">
            exumaaccomodations@gmail.com
        </a>
    </p>
</section>


<!-- Image lightbox -->
<div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="Accommodation photo viewer" aria-hidden="true">
  <button class="lightbox-close" id="lightbox-close" type="button" aria-label="Close image viewer">&times;</button>
  <button class="lightbox-prev" id="lightbox-prev" type="button" aria-label="Previous image">&#10094;</button>
  <img class="lightbox-img" id="lightbox-img" src="" alt="">
  <button class="lightbox-next" id="lightbox-next" type="button" aria-label="Next image">&#10095;</button>
  <div class="lightbox-caption"><span class="lb-name" id="lightbox-name"></span><span class="lb-label" id="lightbox-label"></span></div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
(function () {
    // Each region map has only its own location marker. The luxury section has
    // no separate coordinates supplied, so it shows the Exuma area without a pin.
    var regionMaps = [
        { id: "map-george-town", name: "George Town", coords: [23.51921, -75.78698], zoom: 12 },
        { id: "map-luxury", name: "Exuma", coords: [23.55, -75.8], zoom: 9, marker: false },
        { id: "map-michelson", name: "Michelson", coords: [23.49745, -75.75997], zoom: 13 },
        { id: "map-moss", name: "Moss Town", coords: [23.57422, -75.86730], zoom: 13 },
        { id: "map-staniel", name: "Staniel Cay", coords: [24.17252, -76.44518], zoom: 13 }
    ];
    regionMaps.forEach(function (item) {
        var element = document.getElementById(item.id);
        if (!element || !window.L) return;
        var map = L.map(element).setView(item.coords, item.zoom);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        if (item.marker !== false) {
            L.marker(item.coords).addTo(map).bindPopup(item.name + ", Exuma, Bahamas");
        }
    });
})();
</script>
<script>
(function () {
    "use strict";

    /* ============================================================
       1. ACCOMMODATION DATA
       ============================================================ */

    var PRICES = [180, 240, 370, 430, 560, 670];

    var REGIONS = [
        {
            id: "george-town",
            gridId: "grid-george-town",
            region: "George Town",
            location: "George Town, Great Exuma",
            altPrefix: "George Town accommodation",
            names: [
                "1 Bedroom George Town Retreat",
                "2 Bedroom George Town Premium Retreat",
                "3 Bedroom George Town Villa",
                "4 Bedroom George Town Executive Villa",
                "5 Bedroom George Town Grand Villa",
                "6 Bedroom George Town Estate"
            ],
            descriptions: [
                `Discover an inviting one-bedroom retreat in George Town, thoughtfully suited to couples or solo travellers seeking a comfortable island base. Enjoy an easy-going Exuma stay with room to unwind after a day exploring the island.

1 Bedroom
Beachfront
Wi-Fi included`,
                `A polished two-bedroom retreat offering a little more space for couples, friends or a small family. Settle into the relaxed rhythm of George Town and enjoy a comfortable base for your Great Exuma getaway.

2 Bedrooms
Beachfront
Wi-Fi included`,
                `This three-bedroom villa offers a welcoming balance of shared space and personal comfort for families or friends travelling together. Make it your home base for discovering George Town and the wider island.

3 Bedrooms
Beachfront
Wi-Fi included`,
                `Designed for groups who appreciate room to spread out, this four-bedroom executive villa brings everyone together while leaving space to relax. A considered choice for a family holiday or a getaway with friends in Great Exuma.

4 Bedrooms
Beachfront
Wi-Fi included`,
                `With five bedrooms and generous accommodation capacity, this grand villa is well suited to multi-generational families and larger groups. Enjoy the freedom to share the experience while keeping a comfortable place to retreat.

5 Bedrooms
Beachfront
Wi-Fi included`,
                `A spacious six-bedroom estate for larger gatherings, family celebrations or group escapes. Make the most of time together with a comfortable George Town base and the laid-back appeal of Great Exuma.

6 Bedrooms
Beachfront
Wi-Fi included`
            
            ],
            images: {
                living: function (i) {
                    return i === 1
                        ? "images/accommodations/goergetownlivingrom1.jpg"
                        : "images/accommodations/goergetownlivingroom" + i + ".jpg";
                },
                bedroom: function (i) { return "images/accommodations/goergetownbedroom" + i + ".jpg"; },
                bathroom: function (i) { return "images/accommodations/goergetownbathroom" + i + ".jpg"; }
            }
        },
        {
            id: "luxury-villas",
            gridId: "grid-luxury",
            region: "Luxury Villas",
            location: "Exuma, Bahamas",
            altPrefix: "Luxury accommodation",
            names: [
                "1 Bedroom Luxury Retreat",
                "2 Bedroom Premium Luxury Retreat",
                "3 Bedroom Luxury Villa",
                "4 Bedroom Executive Villa",
                "5 Bedroom Grand Luxury Villa",
                "6 Bedroom Luxury Estate"
            ],
            descriptions: [
                `An elegant one-bedroom escape for guests who value a calm, refined setting. Ideal for a couple or solo traveller, this retreat offers a comfortable base from which to enjoy the natural beauty and easy pace of Exuma.

1 Bedroom
Beachfront
Wi-Fi included`,
                `A sophisticated two-bedroom retreat with space for a couple, friends or a small family to relax in comfort. Enjoy an elevated island stay with the freedom to explore Exuma at your own pace.

2 Bedrooms
Beachfront
Wi-Fi included`,
                `This three-bedroom luxury villa offers a gracious setting for families or friends travelling together. With room to gather and unwind, it provides a welcoming home base for an Exuma escape.

3 Bedrooms
Beachfront
Wi-Fi included`,
                `A four-bedroom executive villa for guests who appreciate generous space and a polished holiday setting. Well suited to families and groups, it makes sharing an Exuma getaway feel effortless.

4 Bedrooms
Beachfront
Wi-Fi included`,
                `Created for larger parties, this five-bedroom grand villa offers room to reconnect, celebrate and enjoy an extended island stay. A considered choice for families or friends seeking a more spacious Exuma retreat.

5 Bedrooms
Beachfront
Wi-Fi included`,
                `A six-bedroom luxury estate offering generous accommodation for larger families and groups. Enjoy the flexibility of a spacious shared retreat while making lasting memories in the distinctive setting of Exuma.

6 Bedrooms
Beachfront
Wi-Fi included`
            
            ],
            images: {
                living: function (i) { return "images/accommodations/luxurylivingroom" + i + ".jpg"; },
                bedroom: function (i) { return "images/accommodations/luxurybedroom" + i + ".jpg"; },
                bathroom: function (i) { return "images/accommodations/luxurybathroom" + i + ".jpg"; }
            }
        },
        {
            id: "michelson-rokers-point",
            gridId: "grid-michelson",
            region: "Michelson",
            location: "Michelson, Exuma",
            altPrefix: "Michelson accommodation",
            names: [
                "1 Bedroom Coastal Retreat",
                "2 Bedroom Premium Coastal Retreat",
                "3 Bedroom Coastal Villa",
                "4 Bedroom Ocean Villa",
                "5 Bedroom Grand Ocean Villa",
                "6 Bedroom Coastal Estate"
            ],
            descriptions: [
                `A welcoming one-bedroom coastal retreat for couples or solo travellers seeking a relaxed base in the Michelson and Roker's Point area. Unwind at your own pace and enjoy the easy-going character of Exuma.

1 Bedroom
Beachfront
Wi-Fi included`,
                `This two-bedroom coastal retreat offers extra room for friends or a small family. With a relaxed island feel and a convenient Michelson-area base, it is a lovely setting for a restorative Exuma stay.

2 Bedrooms
Beachfront
Wi-Fi included`,
                `A three-bedroom coastal villa with space for families and friends to spend quality time together. Enjoy a comfortable base in the Michelson area while discovering the surrounding island communities.

3 Bedrooms
Beachfront
Wi-Fi included`,
                `This four-bedroom ocean villa is suited to larger families or groups who want space to relax between island adventures. Settle into a coastal escape with room for everyone to feel at home.

4 Bedrooms
Beachfront
Wi-Fi included`,
                `A five-bedroom grand ocean villa offering generous room for group getaways and family holidays. Share the experience of Exuma together, with space to gather and unwind after a day out.

5 Bedrooms
Beachfront
Wi-Fi included`,
                `With six bedrooms, this coastal estate is designed for larger groups seeking generous space and a comfortable shared base. Ideal for bringing family or friends together for a memorable stay in Exuma.

6 Bedrooms
Beachfront
Wi-Fi included`
            
            ],
            images: {
                living: function (i) { return "images/accommodations/michelsonlivingroom" + i + ".jpg"; },
                bedroom: function (i) { return "images/accommodations/michelsonbedroom" + i + ".jpg"; },
                bathroom: function (i) { return "images/accommodations/michelsonbathroom" + i + ".jpg"; }
            }
        },
        {
            id: "moss-town",
            gridId: "grid-moss",
            region: "Moss Town",
            location: "Moss Town, Great Exuma",
            altPrefix: "Moss Town accommodation",
            names: [
                "1 Bedroom Moss Town Retreat",
                "2 Bedroom Moss Town Premium Retreat",
                "3 Bedroom Moss Town Villa",
                "4 Bedroom Moss Town Executive Villa",
                "5 Bedroom Moss Town Grand Villa",
                "6 Bedroom Moss Town Estate"
            ],
            descriptions: [
                `A charming one-bedroom retreat for couples or solo travellers looking for a comfortable base in Moss Town. Enjoy a slower island pace and the freedom to shape your own Great Exuma getaway.

1 Bedroom
Beachfront
Wi-Fi included`,
                `This two-bedroom retreat combines a welcoming atmosphere with added room for friends or a small family. A comfortable choice for guests who want to experience Moss Town and the wider island at their own pace.

2 Bedrooms
Beachfront
Wi-Fi included`,
                `A three-bedroom villa offering a relaxed setting for families or friends travelling together. Enjoy space to reconnect and a welcoming home base for your time in Great Exuma.

3 Bedrooms
Beachfront
Wi-Fi included`,
                `With four bedrooms, this executive villa gives larger families and groups room to settle in comfortably. Make it the starting point for an easy-going Moss Town holiday filled with time together and island discovery.

4 Bedrooms
Beachfront
Wi-Fi included`,
                `This five-bedroom grand villa is well suited to larger families and groups seeking generous accommodation. Enjoy the convenience of sharing one base while making the most of a Great Exuma escape.

5 Bedrooms
Beachfront
Wi-Fi included`,
                `A six-bedroom estate offering ample accommodation for larger gatherings and group holidays. With room for everyone, it is a welcoming setting for shared moments and a relaxed stay in Moss Town.

6 Bedrooms
Beachfront
Wi-Fi included`
            
            ],
            images: {
                living: function (i) { return "images/accommodations/mosslivingroom" + i + ".jpg"; },
                bedroom: function (i) { return "images/accommodations/mossbedroom" + i + ".jpg"; },
                bathroom: function (i) { return "images/accommodations/mossbathroom" + i + ".jpg"; }
            }
        },
        {
            id: "staniel-cay-exuma-cays",
            gridId: "grid-staniel",
            region: "Staniel Cay",
            location: "Staniel Cay, Exuma Cays",
            altPrefix: "Staniel Cay accommodation",
            names: [
                "2 Bedroom Staniel Cay Retreat",
                "2 Bedroom Staniel Cay Premium Retreat",
                "3 Bedroom Staniel Cay Villa",
                "4 Bedroom Staniel Cay Island Villa",
                "5 Bedroom Staniel Cay Grand Villa",
                "6 Bedroom Staniel Cay Estate"
            ],
            descriptions: [
                `A comfortable two-bedroom island retreat for couples, friends or a small family eager to experience Staniel Cay. Enjoy a relaxed home base for discovering the character and natural beauty of the Exuma Cays.

2 Bedrooms
Beachfront
Wi-Fi included`,
                `This premium two-bedroom retreat offers a refined, welcoming setting for guests seeking extra comfort during their Staniel Cay stay. Ideal for a couple or small family looking to explore the surrounding cays at an unhurried pace.

2 Bedrooms
Beachfront
Wi-Fi included`,
                `A three-bedroom villa with space for families or friends to share an island escape. Return to a comfortable base after exploring the distinctive scenery and waters of the Exuma Cays.

3 Bedrooms
Beachfront
Wi-Fi included`,
                `This four-bedroom island villa is suited to families and groups who want to experience Staniel Cay together. With room to gather and unwind, it offers a welcoming base for your time in the Exuma Cays.

4 Bedrooms
Beachfront
Wi-Fi included`,
                `A five-bedroom grand villa with generous accommodation for larger families or groups. Share the pleasures of an island getaway while enjoying space to relax and reconnect on Staniel Cay.

5 Bedrooms
Beachfront
Wi-Fi included`,
                `With six bedrooms, this island estate provides generous accommodation for larger groups and family gatherings. Make time together the centre of your stay while exploring the remarkable setting of the Exuma Cays.

6 Bedrooms
Beachfront
Wi-Fi included`
            
            ],
            images: {
                living: function (i) { return "images/accommodations/stanielcaylivingroom" + i + ".jpg"; },
                bedroom: function (i) { return "images/accommodations/stanielcaybedroom" + i + ".jpg"; },
                bathroom: function (i) { return "images/accommodations/stanielcaybathroom" + i + ".jpg"; }
            }
        }
    ];

    /* ============================================================
       2. REGION FILTER
       Supports ?region=george-town or #george-town in the URL.
       If no region is selected, all regions are displayed.
       ============================================================ */
    function getRequestedRegion() {
        var params = new URLSearchParams(window.location.search);
        var fromQuery = params.get("region");
        var fromHash = window.location.hash.replace(/^#/, "");
        return (fromQuery || fromHash || "").toLowerCase();
    }

    function applyRegionFilter() {
        var requested = getRequestedRegion();
        REGIONS.forEach(function (region) {
            var section = document.getElementById(region.id);
            if (!section) return;
            var matches = !requested || region.id === requested || region.gridId === requested;
            section.style.display = matches ? "" : "none";
        });
    }

    /* ============================================================
       3. ACCOMMODATION CARDS
       ============================================================ */
    var lightboxItems = [];

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function (char) {
            return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char];
        });
    }

    function createGallery(region, accommodationIndex, name) {
        var number = accommodationIndex + 1;
        var imageTypes = [
            { label: "Living Room", src: region.images.living(number) },
            { label: "Bedroom", src: region.images.bedroom(number) },
            { label: "Bathroom", src: region.images.bathroom(number) }
        ];
        var html = '<div class="gallery" aria-label="Photo gallery for ' + escapeHtml(name) + '">';
        imageTypes.forEach(function (item) {
            var index = lightboxItems.length;
            lightboxItems.push({ src: item.src, name: name, label: item.label });
            html += '<div class="gallery-item">' +
                '<img src="' + escapeHtml(item.src) + '" alt="' + escapeHtml(region.altPrefix + ' ' + name + ' - ' + item.label) + '" loading="lazy" data-lightbox-index="' + index + '">' +
                '<div class="gallery-label">' + escapeHtml(item.label) + '</div></div>';
        });
        return html + '</div>';
    }

    /*
       Build a complete reservation URL.
       First use booking details passed into accommodations.html in its URL;
       then fall back to values saved by index.html in localStorage.
       This matters because the search form can pass dates in the query string
       without storing them under the same localStorage keys.
    */
    function getBookingValue(queryKeys, storageKeys, fallback) {
        var pageParams = new URLSearchParams(window.location.search);

        for (var i = 0; i < queryKeys.length; i++) {
            var queryValue = pageParams.get(queryKeys[i]);
            if (queryValue !== null && queryValue.trim() !== "") {
                return queryValue.trim();
            }
        }

        for (var j = 0; j < storageKeys.length; j++) {
            var storedValue = null;
            try { storedValue = localStorage.getItem(storageKeys[j]); } catch (e) {}
            if (storedValue !== null && String(storedValue).trim() !== "") {
                return String(storedValue).trim();
            }
        }

        return fallback == null ? "" : String(fallback);
    }

    function buildReserveUrl(region, accommodation, price) {
        var params = new URLSearchParams();
        params.set("region", region.id);
        params.set("accommodation", accommodation);
        params.set("price", String(price));

        var bookingFields = [
            {
                name: "checkin",
                queryKeys: ["checkin", "check_in", "check-in"],
                storageKeys: ["checkin", "check_in", "check-in", "exuma_checkin", "exuma_check_in"]
            },
            {
                name: "checkout",
                queryKeys: ["checkout", "check_out", "check-out"],
                storageKeys: ["checkout", "check_out", "check-out", "exuma_checkout", "exuma_check_out"]
            },
            {
                name: "adults",
                queryKeys: ["adults"],
                storageKeys: ["adults", "exuma_adults"],
                fallback: "2"
            },
            {
                name: "children",
                queryKeys: ["children"],
                storageKeys: ["children", "exuma_children"],
                fallback: "0"
            }
        ];

        bookingFields.forEach(function (field) {
            var value = getBookingValue(field.queryKeys, field.storageKeys, field.fallback);
            if (value !== "") {
                params.set(field.name, value);
                try { localStorage.setItem(field.name, value); } catch (e) {}
            }
        });

        return "reserve.html?" + params.toString();
    }

    function renderCards() {
        REGIONS.forEach(function (region) {
            var grid = document.getElementById(region.gridId);
            if (!grid) return;
            var cards = "";
            region.names.forEach(function (name, i) {
                var price = PRICES[i] || PRICES[0];
                cards += '<article class="card">' +
                    createGallery(region, i, name) +
                    '<h3>' + escapeHtml(name) + '</h3>' +
                    '<div class="card-location">' + escapeHtml(region.location) + '</div>' +
                    '<p class="accommodation-description">' + escapeHtml(region.descriptions[i] || "Comfortable accommodation in Exuma, Bahamas.") + '</p>' +
                    '<div class="info"><div class="price">From $' + price + ' per night</div>' +
                    '<a class="reserve-btn" href="' + buildReserveUrl(region, name, price) + '">Reserve Now</a></div>' +
                    '</article>';
            });
            grid.innerHTML = cards;
        });
    }

    /* ============================================================
       4. IMAGE LIGHTBOX
       ============================================================ */
    var currentLightboxIndex = 0;
    var lightbox = document.getElementById("lightbox");
    var lightboxImage = document.getElementById("lightbox-img");
    var lightboxName = document.getElementById("lightbox-name");
    var lightboxLabel = document.getElementById("lightbox-label");
    var previousButton = document.getElementById("lightbox-prev");
    var nextButton = document.getElementById("lightbox-next");

    function showLightboxImage(index) {
        if (!lightboxItems.length) return;
        currentLightboxIndex = (index + lightboxItems.length) % lightboxItems.length;
        var item = lightboxItems[currentLightboxIndex];
        lightboxImage.src = item.src;
        lightboxImage.alt = item.name + " - " + item.label;
        lightboxName.textContent = item.name;
        lightboxLabel.textContent = item.label;
        previousButton.disabled = lightboxItems.length < 2;
        nextButton.disabled = lightboxItems.length < 2;
        lightbox.classList.add("open");
        lightbox.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
    }

    function closeLightbox() {
        lightbox.classList.remove("open");
        lightbox.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    document.addEventListener("click", function (event) {
        var image = event.target.closest("img[data-lightbox-index]");
        if (image) showLightboxImage(Number(image.getAttribute("data-lightbox-index")));
    });
    document.getElementById("lightbox-close").addEventListener("click", closeLightbox);
    previousButton.addEventListener("click", function () { showLightboxImage(currentLightboxIndex - 1); });
    nextButton.addEventListener("click", function () { showLightboxImage(currentLightboxIndex + 1); });
    lightbox.addEventListener("click", function (event) { if (event.target === lightbox) closeLightbox(); });
    document.addEventListener("keydown", function (event) {
        if (!lightbox.classList.contains("open")) return;
        if (event.key === "Escape") closeLightbox();
        if (event.key === "ArrowLeft") showLightboxImage(currentLightboxIndex - 1);
        if (event.key === "ArrowRight") showLightboxImage(currentLightboxIndex + 1);
    });

    renderCards();
    applyRegionFilter();
})();
</script>

</body>
</html>
