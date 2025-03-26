(define (problem fr_2_4)
    (:domain first-response)
    (:objects
        l1 l2 - location
        v1 v2 v3 v4 - victim
        m1 m2 - medical_unit
    )
    (:init
        (hospital l2)
        (hospital l1)
        (victim-at v1 l2)
        (victim-status v1 hurt)
        (victim-at v2 l1)
        (victim-status v2 hurt)
        (victim-at v3 l1)
        (victim-status v3 dying)
        (victim-at v4 l2)
        (victim-status v4 dying)
        (adjacent l1 l1)
        (adjacent l2 l2)
        (adjacent l2 l1)
        (adjacent l1 l2)
        (medical-unit-at m1 l1)
        (medical-unit-at m2 l2)
    )
    (:goal
        (and
            (victim-status v1 healthy)
            (victim-status v2 healthy)
            (victim-status v3 healthy)
            (victim-status v4 healthy)
        )
    )
)
