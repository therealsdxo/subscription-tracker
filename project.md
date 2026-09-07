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

Incorrect meal counts

Delivering meals after a subscription has expired

Missing customer deliveries

Incorrect subscription expiry calculations

Difficulty identifying active customers

Difficulty tracking payments

Duplicate or inconsistent customer information

Difficulty retrieving customer history

Lack of real-time visibility into business operations

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

# Scope of the application








