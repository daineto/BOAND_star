(define (problem recovery-3x5-cyclic) (:domain icylake)
(:objects
  tile_m1_0 - wall
  tile_m1_1 - wall
  tile_m1_2 - wall
  tile_m1_3 - wall
  tile_m1_4 - wall
  tile_0_m1 - wall
  tile_0_0 - ice
  tile_0_1 - ice
  tile_0_2 - ice
  tile_0_3 - ice
  tile_0_4 - ice
  tile_0_5 - wall
  tile_1_m1 - wall
  tile_1_0 - wall
  tile_1_1 - ice
  tile_1_2 - ice
  tile_1_3 - ice
  tile_1_4 - ice
  tile_1_5 - wall
  tile_2_m1 - wall
  tile_2_0 - wall
  tile_2_1 - wall
  tile_2_2 - ice
  tile_2_3 - ice
  tile_2_4 - wall
  tile_2_5 - wall
  tile_3_0 - wall
  tile_3_1 - wall
  tile_3_2 - wall
  tile_3_3 - wall
  tile_3_4 - wall
)
(:init
  (at tile_0_2)
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
  (left-of tile_m1_3 tile_0_3)
  (left-of tile_0_3 tile_1_3)
  (left-of tile_1_3 tile_2_3)
  (left-of tile_2_3 tile_3_3)
  (left-of tile_m1_4 tile_0_4)
  (left-of tile_0_4 tile_1_4)
  (left-of tile_1_4 tile_2_4)
  (left-of tile_2_4 tile_3_4)
  (down-of tile_0_m1 tile_0_0)
  (down-of tile_0_0 tile_0_1)
  (down-of tile_0_1 tile_0_2)
  (down-of tile_0_2 tile_0_3)
  (down-of tile_0_3 tile_0_4)
  (down-of tile_0_4 tile_0_5)
  (down-of tile_1_m1 tile_1_0)
  (down-of tile_1_0 tile_1_1)
  (down-of tile_1_1 tile_1_2)
  (down-of tile_1_2 tile_1_3)
  (down-of tile_1_3 tile_1_4)
  (down-of tile_1_4 tile_1_5)
  (down-of tile_2_m1 tile_2_0)
  (down-of tile_2_0 tile_2_1)
  (down-of tile_2_1 tile_2_2)
  (down-of tile_2_2 tile_2_3)
  (down-of tile_2_3 tile_2_4)
  (down-of tile_2_4 tile_2_5)
)
(:goal (at tile_0_1))
)
