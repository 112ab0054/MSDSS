import type { ExecArgs } from "@medusajs/framework/types"
import { Modules } from "@medusajs/framework/utils"

export default async function fixture({ container }: ExecArgs) {
  const product = container.resolve(Modules.PRODUCT)
  const order = container.resolve(Modules.ORDER)
  if (!(await product.listProductCollections({ handle: "msdss-verification" })).length) {
    await product.createProductCollections([{ title: "MSDSS Verification Collection", handle: "msdss-verification" }])
  }
  if (!(await product.listProductTypes({ value: "MSDSS Verification Type" })).length) {
    await product.createProductTypes([{ value: "MSDSS Verification Type" }])
  }
  if (!(await product.listProductTags({ value: "MSDSS Verification Tag" })).length) {
    await product.createProductTags([{ value: "MSDSS Verification Tag" }])
  }
  if (!(await order.listReturnReasons({ value: "msdss_verification" })).length) {
    await order.createReturnReasons([{ value: "msdss_verification", label: "MSDSS verification reason" }])
  }
  console.log("MSDSS catalog fixtures created through native Medusa module services")
}
