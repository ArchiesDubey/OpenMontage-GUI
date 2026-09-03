# Universal Topic-Agnostic Character System

This specification defines the **"Egghead" Vector Character Rig**—a minimalist, highly expressive 2D character system designed to be completely **time-period, topic, and niche agnostic**. 

By using a blank-canvas base avatar, you can transport this character into any subject matter—from prehistoric survival to quantum physics, corporate finance, industrial ethics, or neuroscience—with minor modular swaps.

---

## 1. Anatomy of the Base "Egghead" Avatar

```
                 [ Modular Hair / Hat / Headwear ]
                         .-------------.
                       /                 \
                      |     (•)    (•)    |  <-- High-contrast expressive eyes
                      |                   |
                       \      \_____/    /   <-- Single-stroke expressive mouth
                         '-------------'
                                |  <-- Minimalist neck / white collar
                        .---------------+---------------.
                       /                                 \
                      |     [ MODULAR TORSO OUTFIT ]     |
                      |   (T-shirt, Fur, Suit, Coat)     |
                      |                                  |
                      '---------------------------------'
                              / |             | \
                             /  |             |  \
                 Stick Arm -'   |             |   '- Stick Arm
                                |             |
                            [ Pants / Robe / Loincloth ]
                               /               \
                              /                 \
                  Stick Leg -'                   '- Stick Leg
```

### Core Geometric Rules
1. **The Head (The Universal Canvas):**
   * **Color:** Pure Flat White (`#FFFFFF`).
   * **Shape:** Clean circle or slightly vertical ellipse.
   * **Outline:** Thick, crisp, dark ink stroke (`#121212`, 6–8px at 1080p).
   * **Identity:** Completely neutral—no fixed race, ethnicity, or gender markers on the base mesh.
2. **Facial Features (Minimalist Emotional Drivers):**
   * **Eyebrows:** The single most important emotional cue. 1–2 stroke vector arcs that float above or touch the head outline.
   * **Eyes:** 
     * *Normal:* Solid black oval dots (`#111111`).
     * *Shock/Dread:* Outer white circle with tiny black pin-prick pupils.
     * *Skeptical:* One regular eye, one flattened half-closed eye with an underline wrinkle.
     * *Asleep/Serene:* Downward-curved smiling arcs or flat sleepy lines.
   * **Mouth:** Minimalist stroke line without lips or teeth (unless yelling/screaming).
     * *Deadpan:* Straight horizontal line.
     * *Amused:* Subtle asymmetric smirk.
     * *Concerned:* Downward curve.
3. **Limbs & Gestures:**
   * **Arms & Legs:** Bold black stick or simplified tube lines (`#121212`, 4–6px stroke).
   * **Hands:** Simplified mitten shape or 3–4 minimalist finger strokes. High poseability for expressive gesturing (pointing at charts, scratching head, holding props).

---

## 2. The Modular Portability Matrix

The base character never changes geometry. To adapt the character to any niche or time period, you only swap **Headwear**, **Torso Outfit**, and **Key Prop**:

| Topic / Niche | Headwear / Hair | Torso Outfit | Lower Body | Key Contextual Prop |
| :--- | :--- | :--- | :--- | :--- |
| **Prehistoric / Ancient History** | Tousled messy brown hair | Brown rough animal hide/fur wrap | Bare legs / fur loincloth | Flint spear, campfire, stone axe |
| **Modern Life / Neuroscience** | Simple black combed hair | Solid light blue / heather grey crewneck T-shirt | Navy sweatpants | Smartphone, alarm clock, pillow |
| **Industrial / Blue Collar** | Neutral khaki/beige baseball cap | Beige button-up work jumpsuit with rolled sleeves | Matching work trousers | Conveyor belt, sorting tray, clipboard |
| **Corporate / Finance** | Slicked side-part hair | Crisp black or navy suit jacket with white collared shirt & thin tie | Pressed slacks | Briefcase, stock ticker chart, coffee mug |
| **Tech / Software / Crypto** | Tousled hair or backwards cap | Dark charcoal hoodie with rolled-up cuffs | Denim jeans | Glowing laptop with green code lines |
| **Medical / Scientific** | Simple short hair or surgical cap | White laboratory coat over blue scrubs | Scrub pants | Stethoscope, test tube with neon liquid |
| **Medieval / Feudal** | Brown cloth hood or iron kettle hat | Simple coarse linen tunic tied with a rope belt | Brown wool leggings | Wooden pitchfork, parchment scroll |
| **Space / Futuristic** | Clear bubble dome or visor helmet | White pressurized astronaut suit with blue accent patches | Tech boots | Datapad, robotic assistant |

---

## 3. The 12 Core Emotional States

In minimalist animation, facial expressions must communicate complex subtext instantly:

| State | Eyebrows | Eyes | Mouth | Typical Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **1. Neutral / Deadpan** | Straight, horizontal | Standard black dots | Straight horizontal line | Baseline exposition, stating dry facts. |
| **2. Skeptical / Side-Eye** | One raised, one furrowed | Slanted lids looking to side | Small off-center squiggle | Doubting common wisdom, calling out a myth. |
| **3. Existential Dread** | Pinched high in center | Wide white circles, tiny pupils | Small trembling circle | Staggering statistics, realization of mortality. |
| **4. Zen / Peaceful** | Relaxed gentle curves | Closed smiling arcs | Soft subtle upward curve | Relaxing, sleep, ancient leisure. |
| **5. Exhausted / Burnt Out** | Drooping flat | Heavy half-lids with dark bags underneath | Limp flat line, tongue out slightly | Modern 9-to-5, insomnia, overwork. |
| **6. The "Gotcha" Smug** | High confident arch | Confident sideways gaze | Wide asymmetric smirk | Delivering a witty counter-argument. |
| **7. Puzzled / Incredulous** | One high arch, one low frown | Unequal sizes, looking up | Wavy hesitation line | Presenting an evolutionary or economic paradox. |
| **8. Panicked / Overwhelmed** | Angled steep inward | Large wide pupils, sweat drops | Open oval, screaming | Approaching deadlines, predators, market crash. |
| **9. Conniving / Scheming** | Steep downward V-shape | Narrowed slits | Sharp devious grin | Explaining industrial incentives or cartels. |
| **10. Heartbroken / Empathetic**| Slanted upward outward | Glistening wide eyes | Wobbly downturned curve | Discussing suffering, animal culling, loss. |
| **11. Determined / Focused** | Low sharp furrow | Intense concentrated stare | Firm clenched jaw line | Hunting, building an empire, coding late. |
| **12. Shock / Mind Blown** | Lifted off the forehead | Giant white eyes | Jaw dropped to bottom of head | Unveiling the core plot twist or climax stat. |

---

## 4. Scalable Vector & Layer Guidelines

When implementing this character in SVGs, Figma, Remotion, or 2D animation engines:

```
[Character_Rig_Root]
  ├── [Layer_Effects] (Sweat drops, exclamation marks, steam, Zzz)
  ├── [Layer_Head]
  │     ├── Hair_Headwear (Removable)
  │     ├── Eyebrows (Stroke: 5px)
  │     ├── Eyes (Vector Path / Shape)
  │     ├── Mouth (Vector Stroke: 4px)
  │     └── Head_Base (Filled Circle #FFF, Stroke #121212 7px)
  ├── [Layer_Props] (Spear, phone, cup, tool - dynamically attached)
  ├── [Layer_Body]
  │     ├── Arms_Hands (Stroke: 5px with round caps)
  │     ├── Torso_Clothing (Modular color-blocked vector)
  │     └── Legs_Feet (Stroke: 5px with shoe/foot base)
```
