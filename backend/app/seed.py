"""Seed the CoRoute demo: the "World Cup final watch party" group with ~6 months
of history so group memory lands in the demo.

Run with: `make seed`  (==  uv run python -m app.seed)

Idempotent: TRUNCATEs all tables, then reinserts. Uses the table-owner (migrate)
connection so it can write across users while bypassing RLS — seeding only.

Demo logins (dev mode signs in instantly by email):
  alice@coroute.demo  · vegetarian, <=$30, hates loud bars
  bob@coroute.demo    · vegan, <=$25, no car
  cara@coroute.demo   · no diet limit, <=$50, hates long waits
  dan@coroute.demo    · step-free access, <=$35
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Execution,
    Group,
    GroupMember,
    Option,
    Outcome,
    Plan,
    PlanAttendee,
    Preference,
    User,
)
from app.models.enums import (
    ExecutionKind,
    MemberRole,
    PlanStatus,
    PlanType,
    PrefVisibility,
    RsvpStatus,
)

settings = get_settings()
NOW = datetime.now(timezone.utc)

# (display_name, email, prefs)
PEOPLE = [
    ("Alice", "alice@coroute.demo", dict(diet=["vegetarian"], budget_max=30,
                                         vibe_dislikes=["loud bars"])),
    ("Bob", "bob@coroute.demo", dict(diet=["vegan"], budget_max=25,
                                     transportation=["no car"])),
    ("Cara", "cara@coroute.demo", dict(budget_max=50, vibe_dislikes=["long waits"])),
    ("Dan", "dan@coroute.demo", dict(budget_max=35, accessibility_needs=["step-free entry"])),
]

# Past outings, newest-ish first via days_ago. The most recent is The Anchor Sports
# Bar — the live AI generation should avoid suggesting it again.
HISTORY = [
    (28, PlanType.watch_party, "Champions League night", "The Anchor Sports Bar", "Cara"),
    (45, PlanType.dinner, "Birthday dinner", "Otto's Trattoria", "Alice"),
    (61, PlanType.dinner, "Catch-up dinner", "Green Fork Cafe", "Bob"),
    (80, PlanType.activity, "Mini-golf night", "Pin High Mini Golf", "Dan"),
    (98, PlanType.watch_party, "Derby day", "The Anchor Sports Bar", "Cara"),
    (119, PlanType.dinner, "Taco Tuesday", "El Paseo Cantina", "Bob"),
    (140, PlanType.dinner, "Ramen run", "Hokkaido Ramen", "Alice"),
    (165, PlanType.activity, "Bowling", "Strike Lanes", "Dan"),
    (183, PlanType.dinner, "Pizza night", "Forno Vero", "Cara"),
]


def seed(session: Session) -> None:
    session.execute(text(
        "TRUNCATE users, groups, group_members, preferences, plans, plan_attendees, "
        "options, votes, outcomes, executions CASCADE"
    ))

    users: dict[str, User] = {}
    for name, email, _ in PEOPLE:
        u = User(email=email, display_name=name)
        session.add(u)
        users[name] = u
    session.flush()

    group = Group(name="The Group Chat", created_by=users["Alice"].id)
    session.add(group)
    session.flush()

    for i, (name, _, prefs) in enumerate(PEOPLE):
        session.add(GroupMember(
            group_id=group.id, user_id=users[name].id,
            role=MemberRole.owner if i == 0 else MemberRole.member,
        ))
        session.add(Preference(
            group_id=group.id, user_id=users[name].id,
            visibility=PrefVisibility.private, **prefs,
        ))
    session.flush()

    # History: each past outing = an executed plan + the chosen option + outcome
    # + a calendar execution. Outcomes are the group memory fed into new plans.
    for days_ago, ptype, title, venue, picked_by in HISTORY:
        when = NOW - timedelta(days=days_ago)
        plan = Plan(
            group_id=group.id, created_by=users[picked_by].id, type=ptype,
            status=PlanStatus.executed, title=title, scheduled_for=when,
            location="downtown", created_at=when,
        )
        session.add(plan)
        session.flush()
        for name in users:
            session.add(PlanAttendee(
                plan_id=plan.id, user_id=users[name].id,
                rsvp=RsvpStatus.yes, responded_at=when,
            ))
        opt = Option(plan_id=plan.id, title=venue, location="downtown",
                     description=f"{venue} — group's choice for {title.lower()}.",
                     ai_reasoning={"_seeded": True}, rank=1, created_at=when)
        session.add(opt)
        session.flush()
        session.add(Outcome(
            group_id=group.id, plan_id=plan.id, option_id=opt.id,
            summary=venue, happened_at=when,
            extra={"picked_by": picked_by, "title": title},
            created_at=when,
        ))
        session.add(Execution(
            plan_id=plan.id, option_id=opt.id, kind=ExecutionKind.calendar,
            status="created", external_id=f"cal_seed_{plan.id.hex[:8]}",
            payload={"seeded": True}, created_at=when,
        ))
    session.flush()

    # The open plan to demo live: World Cup Final this Sunday. Mixed attendance.
    sunday = NOW + timedelta(days=(6 - NOW.weekday()) % 7 or 7)
    open_plan = Plan(
        group_id=group.id, created_by=users["Alice"].id, type=PlanType.watch_party,
        status=PlanStatus.collecting, title="World Cup Final", scheduled_for=sunday,
        location="downtown",
    )
    session.add(open_plan)
    session.flush()
    rsvps = {"Alice": RsvpStatus.yes, "Bob": RsvpStatus.yes,
             "Cara": RsvpStatus.yes, "Dan": RsvpStatus.maybe}
    for name, rsvp in rsvps.items():
        session.add(PlanAttendee(
            plan_id=open_plan.id, user_id=users[name].id,
            rsvp=rsvp, responded_at=NOW,
        ))
    session.commit()

    print("Seeded demo group 'The Group Chat':")
    print(f"  members: {', '.join(u.display_name for u in users.values())}")
    print(f"  history: {len(HISTORY)} past outings (most recent: {HISTORY[0][3]})")
    print(f"  open plan: '{open_plan.title}' ({sunday.date()}) — 3 yes, 1 maybe")
    print("\nLog in (dev, instant) as any of:")
    for _, email, _ in PEOPLE:
        print(f"  {email}")


def main() -> None:
    url = settings.database_url_migrate or settings.database_url.replace("+asyncpg", "+psycopg")
    engine = create_engine(url)
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    main()
