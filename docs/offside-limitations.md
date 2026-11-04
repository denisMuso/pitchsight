# Offside laboratory limitations

The planar laboratory checks position only: in the opponents' half, nearer the goal line than both the ball and second-last opponent, accounting for attack direction. The halfway line and level players are not offside positions. All opponents count, not just outfield defenders; a goalkeeper need not be the last opponent.

Inputs represent the eligible head/body/feet point projected on the ground, not player centers measured from arbitrary video. Hands/arms do not count. Position is evaluated at the relevant teammate touch; IFAB specifies first contact, with last contact for a goalkeeper throw. The laboratory does not infer contact timing, involvement, interference, deliberate play, deliberate saves, restart exceptions or players temporarily off the field. It never determines an offence.

Each x input has a user-specified bounded error. A conservative ±2u interval compares attacker and reference; overlap returns INCONCLUSIVE. This bound is an assumption, not estimated tracking accuracy. Users can set u=0 only for exact synthetic examples; doing so cannot establish real-world certainty.

Homography uses 4–100 paired non-collinear points with uniqueness, finite-value, conditioning and projection checks. Training-point reprojection residual is reported in pitch metres. Four points can fit exactly even if the selected points are wrong. Planar homography cannot recover elevated body parts, camera motion, rolling shutter or lens distortion. Independent validation correspondences, timing and camera calibration would be required for meaningful measurement.

Source: [current IFAB Law 11](https://www.theifab.com/laws/latest/offside/), read in browser during implementation. This is educational research software, not an IFAB-certified tool.
