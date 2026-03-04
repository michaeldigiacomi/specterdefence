# Test Fixes Plan

## 1. ChangePasswordDialog.tsx
- Add `role="dialog"` to the dialog container
- Add `id` attributes to inputs and `htmlFor` to labels
- Add `aria-label` to close button

## 2. Tenants.tsx
- Add `aria-label` attributes to Edit and Delete buttons

## 3. App.test.tsx
- Fix nested router issue by modifying how App is rendered

## 4. Navigation.test.tsx  
- Fix nested MemoryRouter issue

## 5. Dashboard.test.tsx
- Check button text matching (space vs no space issues)

## 6. useAuth.test.tsx hooks
- These use BrowserRouter in wrapper, should work fine

## 7. useApi.test.tsx
- One test timing out - check MSW handler for PATCH
