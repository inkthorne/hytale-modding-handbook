# Example

THE FILE THAT MATTERS. It sits outside `docs/`, and it reaches into it by a
relative PATH. Both properties are needed: the gate this fixture guards used to
glob `docs/*.md` (so this file was never read) with a link pattern that could not
express a path (so its link would not have matched even if it had been). Either
narrowing alone hides the link, which is why one case cannot cover both and the
`outside` denominator is floored separately.

- [up ok](../../docs/alpha.md#real-section)
