(define (problem open-3x3-s0) (:domain icylake)
(:objects
  tile_m1_0 - wall
  tile_m1_1 - wall
  tile_m1_2 - wall
  tile_0_m1 - wall
  tile_0_0 - ice
  tile_0_1 - ice
  tile_0_2 - ice
  tile_0_3 - wall
  tile_1_m1 - wall
  tile_1_0 - ice
  tile_1_1 - ice
  tile_1_2 - ice
  tile_1_3 - wall
  tile_2_m1 - wall
  tile_2_0 - ice
  tile_2_1 - ice
  tile_2_2 - ice
  tile_2_3 - wall
  tile_3_0 - wall
  tile_3_1 - wall
  tile_3_2 - wall
)
(:init
  (at tile_0_0)
  (left-of tile_m1_0 tile_0_0)
  (left-of tile_0_0 tile_1_0)
  (left-of tile_1_0 tile_2_0)
  (left-of tile_2_0 tile_3_0)
  (left-of tile_m1_1 tile_0_1)
  (left-of tile_0_1 tile_1_1)
  (left-of tile_1_1 tile_2_1)
  (left-of tile_2_1 tile_3_1)
  (left-of tile_m1_2 tile_0_2)
  (left-of tile_0_2 tile_1_2)
  (left-of tile_1_2 tile_2_2)
  (left-of tile_2_2 tile_3_2)
  (down-of tile_0_m1 tile_0_0)
  (down-of tile_0_0 tile_0_1)
  (down-of tile_0_1 tile_0_2)
  (down-of tile_0_2 tile_0_3)
  (down-of tile_1_m1 tile_1_0)
  (down-of tile_1_0 tile_1_1)
  (down-of tile_1_1 tile_1_2)
  (down-of tile_1_2 tile_1_3)
  (down-of tile_2_m1 tile_2_0)
  (down-of tile_2_0 tile_2_1)
  (down-of tile_2_1 tile_2_2)
  (down-of tile_2_2 tile_2_3)
)
(:goal (at tile_2_2))
)
