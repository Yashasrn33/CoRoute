"""Plan routes: create/list under a group, detail, RSVP, and AI option generation."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_rls_session
from app.schemas.plan import (
    AttendeeOut,
    ExecuteIn,
    ExecutionOut,
    OptionOut,
    PlanCreate,
    PlanDetail,
    PlanOut,
    RsvpIn,
    VoteIn,
)
from app.schemas.plan_preference import (
    PlanPreferenceIn,
    PlanPreferenceOut,
    PlanPreferenceSuggestion,
)
from app.services import (
    group_service,
    plan_preference_service,
    plan_service,
    preference_service,
    synthesis,
)

# Plans live under a group for create/list; detail/rsvp/options are addressed by plan id.
group_router = APIRouter(prefix="/groups/{group_id}/plans", tags=["plans"])
plan_router = APIRouter(prefix="/plans", tags=["plans"])


async def _require_member(session: AsyncSession, group_id: UUID) -> None:
    if await group_service.get_group(session, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")


async def _get_plan_or_404(session: AsyncSession, plan_id: UUID):
    plan = await plan_service.get_plan(session, plan_id)
    if plan is None:  # RLS hides non-member plans
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@group_router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    group_id: UUID,
    body: PlanCreate,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanOut:
    await _require_member(session, group_id)
    plan = await plan_service.create_plan(session, group_id, user_id, body)
    return PlanOut.model_validate(plan)


@group_router.get("", response_model=list[PlanOut])
async def list_plans(
    group_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> list[PlanOut]:
    await _require_member(session, group_id)
    return [PlanOut.model_validate(p) for p in await plan_service.list_plans(session, group_id)]


@plan_router.get("/{plan_id}", response_model=PlanDetail)
async def plan_detail(
    plan_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanDetail:
    plan = await _get_plan_or_404(session, plan_id)
    attendees = await plan_service.list_attendees(session, plan_id)
    options = await plan_service.list_options(session, plan_id)
    tallies = await plan_service.vote_tallies(session, plan_id, user_id)
    option_out = []
    for o in options:
        total, mine = tallies.get(o.id, (0, 0))
        out = OptionOut.model_validate(o)
        out.vote_total, out.my_score = total, mine
        option_out.append(out)
    return PlanDetail(
        **PlanOut.model_validate(plan).model_dump(),
        attendees=[
            AttendeeOut(user_id=a.user_id, display_name=u.display_name, rsvp=a.rsvp)
            for a, u in attendees
        ],
        options=option_out,
    )


@plan_router.put("/{plan_id}/rsvp", response_model=PlanDetail)
async def set_rsvp(
    plan_id: UUID,
    body: RsvpIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanDetail:
    await _get_plan_or_404(session, plan_id)
    await plan_service.set_rsvp(session, plan_id, user_id, body.rsvp)
    return await plan_detail(plan_id, user_id, session)


@plan_router.post("/{plan_id}/options", response_model=list[OptionOut])
async def generate_options(
    plan_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> list[OptionOut]:
    plan = await _get_plan_or_404(session, plan_id)
    options = await synthesis.generate_and_store_options(session, plan)
    return [OptionOut.model_validate(o) for o in options]


@plan_router.get("/{plan_id}/preferences/me", response_model=PlanPreferenceOut | None)
async def get_my_plan_prefs(
    plan_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanPreferenceOut | None:
    await _get_plan_or_404(session, plan_id)
    pref = await plan_preference_service.get_my_plan_preference(session, plan_id, user_id)
    return PlanPreferenceOut.model_validate(pref) if pref else None


@plan_router.put("/{plan_id}/preferences/me", response_model=PlanPreferenceOut)
async def put_my_plan_prefs(
    plan_id: UUID,
    body: PlanPreferenceIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanPreferenceOut:
    await _get_plan_or_404(session, plan_id)
    pref = await plan_preference_service.upsert_my_plan_preference(session, plan_id, user_id, body)
    return PlanPreferenceOut.model_validate(pref)


@plan_router.post("/{plan_id}/preferences/suggest", response_model=PlanPreferenceSuggestion)
async def suggest_plan_prefs(
    plan_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanPreferenceSuggestion:
    plan = await _get_plan_or_404(session, plan_id)
    # Seed the suggestion with the caller's OWN general prefs (their data, returned
    # only to them) so it builds on what they already set.
    general = await preference_service.get_my_preference(session, plan.group_id, user_id)
    general_dict = (
        {
            "diet": general.diet, "budget_min": general.budget_min,
            "budget_max": general.budget_max, "vibe_dislikes": general.vibe_dislikes,
            "transportation": general.transportation, "hard_nos": general.hard_nos,
            "accessibility_needs": general.accessibility_needs, "notes": general.notes,
        }
        if general
        else None
    )
    suggestion = await synthesis.suggest_plan_preferences(plan, general_dict)
    return PlanPreferenceSuggestion.model_validate(suggestion)


@plan_router.put("/{plan_id}/votes", response_model=PlanDetail)
async def cast_vote(
    plan_id: UUID,
    body: VoteIn,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> PlanDetail:
    await _get_plan_or_404(session, plan_id)
    await plan_service.cast_vote(session, plan_id, body.option_id, user_id, body.score)
    return await plan_detail(plan_id, user_id, session)


@plan_router.post("/{plan_id}/execute", response_model=ExecutionOut)
async def execute(
    plan_id: UUID,
    body: ExecuteIn,
    _user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_rls_session),
) -> ExecutionOut:
    plan = await _get_plan_or_404(session, plan_id)
    execution = await plan_service.execute_winner(session, plan, body.option_id)
    return ExecutionOut.model_validate(execution)
