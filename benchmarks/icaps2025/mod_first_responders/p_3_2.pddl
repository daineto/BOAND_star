(define (problem fr_3_2)
    (:domain first-response)
    (:objects
        l1 l2 l3 - location
        v1 v2 - victim
        m1 - medical_unit
    )
    (:init
        (hospital l1)
        (victim-at v1 l2)
        (victim-status v1 dying)
        (victim-at v2 l1)
        (victim-status v2 hurt)
        (adjacent l1 l1)
        (adjacent l2 l2)
        (adjacent l3 l3)
        (adjacent l1 l2)
        (adjacent l2 l1)
        (adjacent l3 l1)
        (adjacent l1 l3)
        (adjacent l3 l2)
        (adjacent l2 l3)
        (medical-unit-at m1 l3)
    )
    (:goal
        (and
            (victim-status v1 healthy)
            (victim-status v2 healthy)
        )
    )
)
