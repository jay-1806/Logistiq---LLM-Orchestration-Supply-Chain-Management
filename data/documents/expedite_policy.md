# Expedite Request Policy and Procedures

## 1. Purpose

This document defines the process for evaluating and approving expedite requests 
for customer orders. Expediting an order consumes additional resources (labor, 
carrier costs, warehouse prioritization) and must be justified.

## 2. Decision Framework

When an expedite request comes in, evaluate the following criteria IN ORDER:

### Step 1: Check Order Eligibility
- Is the order currently in "pending" or "processing" status?
- If "shipped" or "delivered" → reject (too late to expedite)
- If "cancelled" → reject (order no longer active)

### Step 2: Check Inventory Availability
- Can the order be fulfilled from current stock without going below reorder point?
- If fulfilling this order drops inventory below reorder point, check if there 
  are other critical orders that would be impacted
- If inventory is insufficient → reject and suggest alternative timeline

### Step 3: Assess Impact on Other Orders
- Are there other orders for the same product that ship sooner?
- Expediting one order must NOT delay another customer's critical order
- If conflict exists → escalate to Supply Chain Manager

### Step 4: Check Carrier Capacity
- Is a faster carrier available for the requested ship date?
- Get carrier quote for expedited service
- Calculate cost delta vs. standard shipping

### Step 5: Approval
| Scenario | Approver |
|----------|----------|
| Cost delta < $500 | Team Lead |
| Cost delta $500 - $5,000 | Supply Chain Manager |
| Cost delta > $5,000 | VP of Operations |
| Customer absorbs cost | Team Lead (any amount) |

## 3. Recommendations

- **Approve** if: inventory is available, no impact on other critical orders, 
  and cost is justified by customer relationship value
- **Reject** if: inventory is insufficient, would delay other critical orders, 
  or cost exceeds customer lifetime value
- **Negotiate** if: partial expedite is possible (e.g., ship 50% now, rest later)

## 4. Documentation

All expedite decisions must be documented with:
- Original order details
- Decision rationale
- Approver name
- Any additional costs incurred
- Final delivery commitment
