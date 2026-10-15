# asset-ids fixture

A miniature of everything `maintenance/scripts/check-asset-ids.py` reads, with known
answers. Driven by `maintenance/scripts/check-asset-ids-fixture.py` (`--mutations` reverts each
guard and asserts the exact set of cases that turns red; it runs on every `verify-docs.sh`).

- `corpus/assets/Server/` - the shipped assets: seven stores (Item/Items, Item/Interactions,
  Audio/SoundEvents, Entity/Effects, Particles with its two non-.json extensions, Drops, and
  Item/Block/Spawners, which ties with Drops), one store declared and absent, one file that does not
  parse, and Prefabs/ and World/ bulk data that must stay out of the sweep. The usages that TYPE the
  keys live inside the item and interaction files: the mixture key `Build` (nine sounds, one particle),
  `Id` that means items under `Rewards` and sounds under `Cues`, a map under `SoundMap` and one with a
  field among its values (`Tones`), `Solid` holding the built-in `Empty`, and `Lonely`, seen under a
  single parent.
- `corpus/src/Registry.java` - the `setPath` registrations the store list is mined from.
- `corpus/packs/` - stand-ins for `examples/custom-food` and `examples/custom-drop`.
- `corpus/docs/` - six pages. `families.md` holds a real, an invented and a wrong-kind id per family and
  the typing cases; `exempt.md` has the placeholder note, a pack reference and page-defined paths;
  `bare.md` repeats the same ids with none of that; `pack2.md` names the other pack; `shapes.md` holds
  values that are not ids; `fences.md` holds the fence shapes (comments, `...`, a fragment, an untagged
  JSON fence, an indented one, and a tree and a java fence that must not be read).
- `typing-snapshot.txt` - the typing table with one class removed, one invented and one retargeted, so the
  drift line is asserted as "1 added, 1 removed, 1 retargeted".

The corpus is static on purpose: `git diff` shows exactly which shipped usage a change touched. The pair
counts in the fixture script change whenever a file here does; the script's `SWEEP` / `TYPING` / `SCAN`
/ `PAIRS` constants are the denominators and are meant to move loudly.
