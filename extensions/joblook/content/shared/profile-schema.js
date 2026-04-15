// Mirrors services/joblook-backend/app/schemas.py. Keep in sync.

export const FIELD_ALIASES = {
  // identity
  "identity.first_name":      ["first_name", "fname", "firstname", "given_name", "givenname", "first name", "given name"],
  "identity.last_name":       ["last_name", "lname", "lastname", "family_name", "familyname", "surname", "last name", "family name"],
  "identity.preferred_name":  ["preferred_name", "preferred name", "nickname"],
  "identity.email":           ["email", "email_address", "e-mail", "work_email"],
  "identity.phone":           ["phone", "phone_number", "mobile", "telephone", "cell"],
  "identity.address_line1":   ["address", "street", "address_line_1", "address1", "street_address"],
  "identity.address_line2":   ["address_line_2", "address2", "apt", "suite", "unit"],
  "identity.city":            ["city", "town", "locality"],
  "identity.state":           ["state", "region", "province"],
  "identity.postal_code":     ["zip", "zipcode", "postal_code", "postcode"],
  "identity.country":         ["country"],
  "identity.linkedin_url":    ["linkedin", "linkedin_url", "linkedin profile"],
  "identity.github_url":      ["github", "github_url"],
  "identity.portfolio_url":   ["website", "portfolio", "portfolio_url", "personal_site"],
  "identity.pronouns":        ["pronouns"],

  // work auth
  "work_authorization.us_work_authorized":        ["legally_authorized", "work_authorized_us", "authorized_to_work"],
  "work_authorization.requires_sponsorship_now":  ["require_sponsorship", "need_sponsorship", "visa_sponsorship"],
  "work_authorization.requires_sponsorship_future": ["future_sponsorship"],

  // preferences
  "preferences.desired_titles":      ["desired_title", "target_role"],
  "preferences.desired_locations":   ["desired_location", "preferred_location"],
  "preferences.remote_preference":   ["remote_preference", "work_location_preference"],
  "preferences.willing_to_relocate": ["willing_to_relocate", "relocate"],
  "preferences.min_salary_usd":      ["salary", "expected_salary", "desired_salary", "min_salary"],
  "preferences.earliest_start_date": ["start_date", "available_start_date", "earliest_start"],
  "preferences.notice_period_weeks": ["notice_period", "notice"],
};

export function getPath(obj, path) {
  const parts = path.split(".");
  let cur = obj;
  for (const p of parts) {
    if (cur == null) return undefined;
    cur = cur[p];
  }
  return cur;
}
