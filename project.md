# 1. Introduction

**HealthX** is a centralized meal subscription management application designed to manage and monitor customers enrolled in recurring healthy meal plans for a meal-delivery business.

In a subscription-based meal delivery operation, each customer may have a different meal package, meal consumption frequency, delivery schedule, dietary preference, payment status, and subscription timeline. As the number of customers increases, managing this information manually can become difficult and can lead to inaccurate meal counts, missed deliveries, expired subscriptions, or inconsistent customer records.

HealthX is designed to solve this problem by providing a structured digital system that acts as a **single source of truth** for all customer and subscription-related information.

The business currently offers three meal subscription packages:

| Package | Meals Included | Maximum Subscription Duration | Price(in INR)
|---|---:|---:|---:|
| 25 Meal Package | 25 meals | 50 days | 6500
| 50 Meal Package | 50 meals | 100 days | 9500
| 90 Meal Package | 90 meals | 180 days | 14500

Each subscription is governed by both the **number of meals allocated** and a **maximum validity period**.

For example, a customer enrolled in the 25 Meal Package receives 25 meals, but those meals must be consumed within 50 days from the package start date. Similarly, the 50 Meal Package must be consumed within 100 days, while the 90 Meal Package must be consumed within 180 days.

Therefore, a subscription may end under either of the following conditions:

1. The customer consumes all meals allocated to the package.
2. The maximum validity period of the subscription is reached.

HealthX will manage the complete subscription lifecycle, including:

- Customer registration
- Meal package allocation
- Subscription start and expected expiry dates
- Total meals allocated
- Meals delivered
- Meals remaining
- Delivery schedules
- Dietary preferences
- Payment status
- Subscription status

The application will also maintain customer information in a centralized database.

Each customer record will contain information such as:

- `customer_name`
- `customer_address`
- `customer_phoneNo`
- `customer_package`
- `customer_numberOfMeals`
- `customer_mealsLeft`
- `customer_packageStartDate`
- `customer_expectedEndDate`
- `payment_status`
- `subscription_status`
- `resubscribe_number`

The purpose of HealthX is to replace fragmented or manual subscription tracking with a reliable and structured system that provides accurate, real-time visibility into customer memberships and meal consumption.

By maintaining customer, subscription, payment, and delivery information in one system, HealthX will help improve operational efficiency, reduce manual errors, and make it easier for the business to manage a growing number of recurring meal subscriptions.

The system will also provide a technical foundation for future features such as automated subscription expiry alerts, WhatsApp notifications, payment reminders, delivery planning, customer analytics, reporting, and other business automations.
No meals are delivered on tuesday as the outlet remains closed on tuesdays.


# 2. Problem Statement

A healthy meal delivery business operates with customers who subscribe to meal packages containing a predefined number of meals.

Each customer may have different:

- Meal package
- Package start date
- Number of meals 
- Number of meals remaining 
- Delivery frequency 
- Dietary preference
- Payment Status
- Subscription Expiry Date

Managing this information manually becomes increasingly difficult as the number of customers grows.
Manual tracking can result in problems such as:

- Incorrect meal counts

- Delivering meals after a subscription has expired
- Missing customer deliveries
- Incorrect subscription expiry calculations
- Difficulty identifying active customers
- Difficulty tracking payments
- Duplicate or inconsistent customer information
- Difficulty retrieving customer history
- Lack of real-time visibility into business operations

HealthX is intended to solve these problems by centralizing customer and subscription information within a structured application and database.


# 3. Project Objective

The primary objective of HealthX is to create a reliable system for managing meal subscriptions from customer registration until subscription completion or expiry.

Key Objectives are:
- Maintaining Centralised customer database
- Store customers contact and delivery information
- Assign meal package to customers
- Track total number of active meals 
- Track meals consumed.
- Track meals remaining.
- Automatically calculate package expiry dates.
- Track subscription status.
- Track payment status.
- Store dietary preferences.
- Manage customer delivery schedules.
- Prevent meals from being delivered after package expiry.
- Reduce manual operational errors.
- Allow staff to quickly search and retrieve customer information.
- Provide accurate information about active, completed, and expired subscriptions.
- Create a foundation for future automation, analytics, and reporting.

# 4. Scope of the application

The initial version of the app should have:

### Customer Management 

The application should allow users to: 

- Create customer record
- View customer details 
- Update customer information
- Search customers
- View customer subscription information

### Subscription Management
The system should:

- Create a meal package
- Assign a meal package to a customer 
- Set a subscription start date 
- Calculate the subscription expiry date
- Track subscription status
- Track meals allocated

### Meal Tracking
The system should:

- Record every delivered meal
- Reduce customers remaining meal balance
- Maintain history of delivered meals

### Delivery Management 
The system should store:

- Delivery address
- Delivery schedule of each customer 
- Dietary instructions
- Delivery status

### Payment Management
The system should store:

- Package price
- Amount paid
- Outstanding amount
- Payment status 
- Payment date

### Subscription Monitoring 
The system should:

- Track active subscriptions
- Completed subscriptions
- Expired subscriptions
- Renewed subscriptions
- Subscriptions approaching expiry 
- Number of times the customer has renewed the plan 

# 5. Meal Packages
HealthX allows authorized users to create and manage custom meal subscription packages based on the business's operational requirements.

Instead of restricting the system to predefined packages, users can define a package by specifying details such as:

- Package name
- Number of meals included
- Maximum validity period
- Package price 
- Package description 
- Package status 

For example a user may create packages like 

| Package | Meals Included | Maximum Subscription Duration | Price(in INR)
|---|---:|---:|---:|
| 25 Meal Package | 25 meals | 50 days | 6500
| 50 Meal Package | 50 meals | 100 days | 9500
| 90 Meal Package | 90 meals | 180 days | 14500

These packages are examples and are not hardcoded into the application.

An authorized user should be able to create new packages whenever required.
For example, the business may later introduce:

- 10 Meal Trial Package
- 30 Meal Monthly Package
- 60 Meal Transformation Package
- 120 Meal Long-Term Package

Each package should define its own meal allocation and validity period.
The subscription validity period begins from the package start date.
When a package is assigned to a customer, the system should automatically calculate the expected expiry date using:

Expected End Date = Package Start Date + Package Validity Days

For example, if a package contains 25 meals with a validity period of 50 days and the subscription begins on 01 September 2026, the system should calculate the expected expiry date based on 50 days from the start date.
Any unused meals remaining after the subscription expiry date should no longer be considered valid unless an authorized user explicitly extends or modifies the subscription.

Authorized users should also be able to:
- Create a new meal package
- View existing packages
- Update package details
- Activate or deactivate packages
- Change package pricing
- Modify the number of meals
- Modify package validity duration

A package that has already been used in previous subscriptions should not normally be permanently deleted, since historical subscription records may depend on it. Instead, the package should be marked as inactive.

