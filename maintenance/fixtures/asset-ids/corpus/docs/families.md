# Families

One page, one of everything the gate has to tell apart. Real ids are in the first fence,
invented ones in the second, real-but-wrong-kind ones in the third.

```json
{ "ItemId": "Sword_A", "Next": "Int_A", "LocalSoundEventId": "SFX_A", "EffectId": "Fx_A", "SystemId": "P_A", "DropListId": "D_A" }
```

```json
{ "ItemId": "Sword_Fake", "Next": "Int_Fake", "LocalSoundEventId": "SFX_Fake", "EffectId": "Fx_Fake", "SystemId": "P_Fake", "DropListId": "D_Fake" }
```

```json
{ "ItemId": "SFX_A", "Next": "Sword_A", "LocalSoundEventId": "Fx_A", "EffectId": "P_A", "SystemId": "D_A", "DropListId": "Int_A" }
```

A tie, an id keyed by a different file extension, and a nested file:

```json
{ "DropListId": "S_ONLY", "SystemId": "Spawn_A", "ItemId": "Axe_C" }
```

Arrays inherit their key, and a map value is typed by its parent:

```json
{
  "Interactions": ["Int_B", "Int_Fake_Arr"],
  "SoundMap": { "Fly": "SFX_F", "Dive": "SFX_Fake_Map" },
  "Tones": { "Zeta": "SFX_Fake_Zeta", "Style": "quiet" }
}
```

A key that means different things under different parents is typed by the pair:

```json
{
  "Rewards": [{ "Id": "Sword_B" }, { "Id": "Id_Fake_Reward" }, { "Id": "SFX_B" }],
  "Cues": [{ "Id": "SFX_C" }, { "Id": "Id_Fake_Cue" }, { "Id": "Sword_B" }],
  "Other": [{ "Id": "Anything_Goes" }]
}
```

A bare-key class that is a mixture of two fields is widened by the evidence at the exact position:

```json
{ "Dust": { "Build": "P_B" }, "Smoke": { "Build": "Nothing_Real" }, "SoundEvents": { "Build": "SFX_B" } }
```

A value the shipped assets themselves put under the key, and a generated state id:

```json
[ { "Solid": "Empty" }, { "Solid": "Sword_B" }, { "Solid": "*Sword_A_State_Broken" }, { "Solid": "*Ghost_State_X" }, { "Solid": "Nothing" } ]
```

A bare-key class seen under one parent only types that parent, not a parent the assets never show it under:

```json
{ "Holder": { "Lonely": "Sword_Fake_L" }, "Elsewhere": { "Lonely": "Anything_L" } }
```
