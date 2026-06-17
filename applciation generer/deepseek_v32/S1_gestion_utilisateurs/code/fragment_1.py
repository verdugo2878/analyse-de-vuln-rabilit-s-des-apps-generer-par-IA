@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin():
        abort(403)
    
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role='admin').count()
    
    return render_template('admin.html', 
                          users_count=total_users,
                          active_users_count=active_users,
                          admins_count=admin_users)
