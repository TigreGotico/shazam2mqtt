# Home Assistant Dashboard Cards

These cards go into the Lovelace UI (**Settings → Dashboards → Edit**).
Replace `living_room` with whatever `DEVICE_NAME` you set.

---

## 1. Full "Now Playing" card (Markdown + artwork + lyrics)

A rich card that shows the album cover, track and artist, metadata, streaming links, and lyrics.

```yaml
type: markdown
title: Now Playing
content: >
  {% set art = state_attr('sensor.living_room_shazam_now_playing', 'artwork_url') %}
  {% set apple = state_attr('sensor.living_room_shazam_now_playing', 'apple_music_url') %}
  {% set spotify = state_attr('sensor.living_room_shazam_now_playing', 'spotify_url') %}
  {% set deezer = state_attr('sensor.living_room_shazam_now_playing', 'deezer_url') %}
  {% set lyrics = state_attr('sensor.living_room_shazam_now_playing', 'lyrics') %}
  {% set meta = state_attr('sensor.living_room_shazam_now_playing', 'metadata') %}

  {% if art and art != 'Unknown' %}
  <img src="{{ art }}" style="width:100%; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.3);">
  {% endif %}

  <h2 style="margin:8px 0 4px;">{{ states('sensor.living_room_shazam_track') }}</h2>
  <p style="margin:0; opacity:0.7; font-size:1.1em;">{{ states('sensor.living_room_shazam_artist') }}</p>

  <p>
  {% if apple and apple != 'Unknown' %}<a href="{{ apple }}" target="_blank">Apple Music</a>{% endif %}
  {% if spotify and spotify != 'Unknown' %} · <a href="{{ spotify }}" target="_blank">Spotify</a>{% endif %}
  {% if deezer and deezer != 'Unknown' %} · <a href="{{ deezer }}" target="_blank">Deezer</a>{% endif %}
  </p>

  {% if meta %}
  <hr>
  <p style="font-size:0.9em; opacity:0.6;">
  {% for k,v in meta.items() %}{{ k }}: {{ v }}{% if not loop.last %} · {% endif %}{% endfor %}
  </p>
  {% endif %}

  {% if lyrics and lyrics != 'Unknown' %}
  <hr>
  <p style="font-style:italic; opacity:0.8; white-space:pre-line;">{{ lyrics[:300] }}{% if lyrics | length > 300 %}…{% endif %}</p>
  {% endif %}
```

---

## 2. Compact card with artwork picture

Uses the `entity_picture` attribute directly. No camera workaround is needed.

```yaml
type: vertical-stack
cards:
  - type: picture
    image: "{{ state_attr('sensor.living_room_shazam_now_playing', 'entity_picture') }}"
    tap_action:
      action: url
      url_path: "{{ state_attr('sensor.living_room_shazam_now_playing', 'apple_music_url') }}"

  - type: entities
    entities:
      - entity: sensor.living_room_shazam_now_playing
        name: Now Playing
      - entity: sensor.living_room_shazam_artist
        name: Artist
      - entity: sensor.living_room_shazam_confidence
        name: Confidence
      - entity: binary_sensor.living_room_shazam_matched
        name: Matched

  - type: markdown
    content: >
      {% set apple = state_attr('sensor.living_room_shazam_now_playing', 'apple_music_url') %}
      {% set spotify = state_attr('sensor.living_room_shazam_now_playing', 'spotify_url') %}
      {% if apple and apple != 'Unknown' %}[Apple Music]({{ apple }}){% endif %}
      {% if spotify and spotify != 'Unknown' %} · [Spotify]({{ spotify }}){% endif %}
```

---

## 3. Mushroom Template card (needs [Mushroom](https://github.com/piitaya/lovelace-mushroom))

A compact card with a picture and streaming links.

```yaml
type: custom:mushroom-template-card
primary: "{{ states('sensor.living_room_shazam_track') }}"
secondary: "{{ states('sensor.living_room_shazam_artist') }} - {{ states('sensor.living_room_shazam_status') }}"
icon: mdi:music-note
entity: sensor.living_room_shazam_now_playing
picture: "{{ state_attr('sensor.living_room_shazam_now_playing', 'entity_picture') }}"
badge_icon: |-
  {% if is_state('binary_sensor.living_room_shazam_matched', 'on') %}
    mdi:check-circle
  {% else %}
    mdi:minus-circle
  {% endif %}
badge_color: |-
  {% if is_state('binary_sensor.living_room_shazam_matched', 'on') %}
    green
  {% else %}
    grey
  {% endif %}
tap_action:
  action: url
  url_path: "{{ state_attr('sensor.living_room_shazam_now_playing', 'apple_music_url') }}"
hold_action:
  action: more-info
multiline_secondary: true
layout: horizontal
fill_container: true
```

---

## 4. Mini player style

A narrow strip that shows only the track, artist, and the album cover as background.

```yaml
type: custom:mushroom-template-card
primary: "{{ states('sensor.living_room_shazam_track') }}"
secondary: "{{ states('sensor.living_room_shazam_artist') }}"
picture: "{{ state_attr('sensor.living_room_shazam_now_playing', 'entity_picture') }}"
layout: vertical
tap_action:
  action: url
  url_path: "{{ state_attr('sensor.living_room_shazam_now_playing', 'apple_music_url') }}"
```

---

## Tips

- **Old artwork lingering?** The `entity_picture` attribute clears automatically when the state becomes `unknown` or `silence`.
- **Track too long?** Adjust `REQUIRED_NO_MATCHES` in your `.env` file so brief drop-outs do not reset the card.
- **Want lyrics in a separate card?** Extract just the lyrics block from card #1 into its own `markdown` card.

---
[← Home Assistant](home_assistant.md) · [Home](README.md) · [Troubleshooting →](troubleshooting.md)
