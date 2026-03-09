import { useState } from 'react';
import { Users as UsersIcon, Plus, Edit2, Shield, ShieldAlert, CheckCircle, XCircle, Building2, Trash2 } from 'lucide-react';
import { useUsers, useCreateUser, useUpdateUser, useUserTenants, useTenants, useAssignUserTenant, useUnassignUserTenant } from '@/hooks/useApi';
import { UserInternal, UserCreate, UserUpdate, Tenant } from '@/types';
import toast from 'react-hot-toast';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function Users() {
  const [showModal, setShowModal] = useState(false);
  const [showTenantModal, setShowTenantModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserInternal | null>(null);
  const [formData, setFormData] = useState<Partial<UserCreate> & Partial<UserUpdate>>({});
  
  const { data: usersData, isLoading: usersLoading } = useUsers();
  const { data: allTenantsData } = useTenants();
  
  const createUser = useCreateUser();
  const updateUser = useUpdateUser(editingUser?.id || 0);
  const assignTenant = useAssignUserTenant();
  const unassignTenant = useUnassignUserTenant();

  const handleOpenModal = (user?: UserInternal) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        is_admin: user.is_admin,
        is_active: user.is_active,
      });
    } else {
      setEditingUser(null);
      setFormData({ is_admin: false, is_active: true });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingUser(null);
    setFormData({});
  };

  const handleOpenTenantModal = (user: UserInternal) => {
    setEditingUser(user);
    setShowTenantModal(true);
  };

  const handleCloseTenantModal = () => {
    setShowTenantModal(false);
    setEditingUser(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingUser) {
        await updateUser.mutateAsync(formData as UserUpdate);
        toast.success('User updated successfully');
      } else {
        await createUser.mutateAsync(formData as UserCreate);
        toast.success('User created successfully');
      }
      handleCloseModal();
    } catch (err) {
      toast.error(editingUser ? 'Failed to update user' : 'Failed to create user');
    }
  };

  const handleAssignTenant = async (tenantId: string) => {
    if (!editingUser) return;
    try {
      await assignTenant.mutateAsync({ userId: editingUser.id, tenantId });
      toast.success('Tenant assigned successfully');
    } catch (err) {
      toast.error('Failed to assign tenant');
    }
  };

  const handleUnassignTenant = async (tenantId: string) => {
    if (!editingUser) return;
    try {
      await unassignTenant.mutateAsync({ userId: editingUser.id, tenantId });
      toast.success('Tenant unassigned successfully');
    } catch (err) {
      toast.error('Failed to unassign tenant');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <UsersIcon className="w-6 h-6 text-primary-500" />
            User Management
          </h1>
          <p className="mt-1 text-gray-500 dark:text-gray-400">
            Manage application users and their tenant access
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Username</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Last Login</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {usersLoading ? (
                [1, 2, 3].map((i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48"></div></td>
                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16 ml-auto"></div></td>
                  </tr>
                ))
              ) : usersData?.items?.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/40 flex items-center justify-center text-primary-600 dark:text-primary-400 font-bold text-sm uppercase">
                        {user.username.charAt(0)}
                      </div>
                      <span className="font-medium text-gray-900 dark:text-white">{user.username}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
                      user.is_admin
                        ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400'
                        : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                    )}>
                      {user.is_admin ? <ShieldAlert className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                      {user.is_admin ? 'Admin' : 'User'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium',
                      user.is_active
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                    )}>
                      {user.is_active ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      {user.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleOpenTenantModal(user)}
                        className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                        title="Manage Tenants"
                      >
                        <Building2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleOpenModal(user)}
                        className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                        title="Edit User"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* User Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editingUser ? `Edit ${editingUser.username}` : 'Add New User'}
              </h2>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {!editingUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Username *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.username || ''}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                    placeholder="e.g. jdoe"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {editingUser ? 'Reset Password (optional)' : 'Password *'}
                </label>
                <input
                  type="password"
                  required={!editingUser}
                  value={formData.password || ''}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 dark:text-white"
                  placeholder={editingUser ? '••••••••' : 'Enter password'}
                />
              </div>

              <div className="flex flex-col gap-3 pt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_admin}
                    onChange={(e) => setFormData({ ...formData, is_admin: e.target.checked })}
                    className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Administrator access</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-primary-500 rounded border-gray-300 focus:ring-primary-500"
                  />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Account enabled</span>
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-6">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createUser.isPending || updateUser.isPending}
                  className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 transition-colors"
                >
                  {editingUser ? 'Update User' : 'Create User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tenant Assignment Modal */}
      {showTenantModal && editingUser && (
        <TenantAssignmentModal
          user={editingUser}
          allTenants={allTenantsData?.items || []}
          onClose={handleCloseTenantModal}
          onAssign={handleAssignTenant}
          onUnassign={handleUnassignTenant}
        />
      )}
    </div>
  );
}

function TenantAssignmentModal({ 
  user, 
  allTenants, 
  onClose,
  onAssign,
  onUnassign
}: { 
  user: UserInternal; 
  allTenants: Tenant[];
  onClose: () => void;
  onAssign: (id: string) => Promise<void>;
  onUnassign: (id: string) => Promise<void>;
}) {
  const { data: userTenants, isLoading } = useUserTenants(user.id);
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  const assignedIds = new Set(userTenants?.map(t => t.id) || []);
  
  const handleToggle = async (tenant: Tenant) => {
    setIsProcessing(tenant.id);
    try {
      if (assignedIds.has(tenant.id)) {
        await onUnassign(tenant.id);
      } else {
        await onAssign(tenant.id);
      }
    } finally {
      setIsProcessing(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Manage Tenant Access: {user.username}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Select the tenants this user is allowed to manage
          </p>
        </div>

        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 animate-pulse rounded-lg" />)}
            </div>
          ) : (
            <div className="space-y-2">
              {allTenants.map((tenant) => (
                <div 
                  key={tenant.id}
                  className={cn(
                    "flex items-center justify-between p-3 rounded-lg border transition-all",
                    assignedIds.has(tenant.id)
                      ? "bg-primary-50 dark:bg-primary-900/10 border-primary-200 dark:border-primary-800"
                      : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-10 h-10 rounded-lg flex items-center justify-center",
                      assignedIds.has(tenant.id) ? "bg-primary-100 text-primary-600" : "bg-gray-100 text-gray-400"
                    )}>
                      <Building2 className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{tenant.name}</p>
                      <p className="text-xs text-gray-500 font-mono truncate max-w-[200px]">{tenant.tenant_id}</p>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => handleToggle(tenant)}
                    disabled={!!isProcessing}
                    className={cn(
                      "px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors",
                      assignedIds.has(tenant.id)
                        ? "bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
                        : "bg-primary-50 text-primary-600 hover:bg-primary-100 dark:bg-primary-900/20 dark:text-primary-400"
                    )}
                  >
                    {isProcessing === tenant.id ? "..." : assignedIds.has(tenant.id) ? "Remove" : "Assign"}
                  </button>
                </div>
              ))}
              {allTenants.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-gray-500">No tenants available. Create one first.</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
