(define (problem fr_6_1)
    (:domain first-response)
    (:objects
        l1 l2 l3 l4 l5 l6 - location
        f1 f2 f3 f4 f5 - fire_unit
        v1 - victim
        m1 - medical_unit
    )
    (:init
        (hospital l4)
        (hospital l1)
        (water-at l4)
        (water-at l6)
        (water-at l3)
        (fire l5)
        (victim-at v1 l2)
        (victim-status v1 dying)
        (adjacent l1 l1)
        (adjacent l2 l2)
        (adjacent l3 l3)
        (adjacent l4 l4)
        (adjacent l5 l5)
        (adjacent l6 l6)
        (adjacent l3 l1)
        (adjacent l1 l3)
        (adjacent l3 l2)
        (adjacent l2 l3)
        (adjacent l4 l1)
        (adjacent l1 l4)
        (adjacent l4 l2)
        (adjacent l2 l4)
        (adjacent l4 l3)
        (adjacent l3 l4)
        (adjacent l5 l1)
        (adjacent l1 l5)
        (adjacent l5 l2)
        (adjacent l2 l5)
        (adjacent l5 l3)
        (adjacent l3 l5)
        (adjacent l6 l1)
        (adjacent l1 l6)
        (adjacent l6 l2)
        (adjacent l2 l6)
        (adjacent l6 l3)
        (adjacent l3 l6)
        (adjacent l6 l4)
        (adjacent l4 l6)
        (adjacent l6 l5)
        (adjacent l5 l6)
        (fire-unit-at f1 l1)
        (fire-unit-at f2 l3)
        (fire-unit-at f3 l6)
        (fire-unit-at f4 l3)
        (fire-unit-at f5 l5)
        (medical-unit-at m1 l2)
    )
    (:goal
        (and
            (nfire l5)
            (victim-status v1 healthy)
        )
    )
)
